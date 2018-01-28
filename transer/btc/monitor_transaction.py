import decimal
from collections import defaultdict

from bitcoinrpc.authproxy import JSONRPCException

from transer.exceptions import BtcMonitorTransactionException
from transer.btc import _btc_dispatcher
from transer.db import btc, sqla_session

from sqlalchemy import desc
from sqlalchemy.orm.exc import NoResultFound


@_btc_dispatcher.add_method
def get_recent_deposit_transactions(bt_name, confirmations=6, update_amounts=True):
    """
    pull-проверяльщик новых входящих (receive) транзакций, для заданного количества конфирмаций
    гарантирует однократный учёт входящих транзакций (only-once semantics)

    :param bt_name: name to lookup in btc.BitcoindInstance, as str
    :param confirmations: минимальное количетство подтверждений, для которого проверяется наличие новых транзакций;
        является дискриминатором: для разных величин алгоритм отрабатывает независимо
    :param update_amounts: обновлять/инкрементировать количество денег в кошельках btc.Address согласно найденным
        входящим транзакциям
    :return:
    """

    # explicitly prohibit mempool/unconfirmed transactions to prevent race conditions
    if confirmations <= 0:
        return {}

    try:
        bitcoind_inst = btc.BitcoindInstance.query.filter_by(instance_name=bt_name).one()
    except NoResultFound:
        raise BtcMonitorTransactionException(f'Bitcoind RPC server with name {bt_name} not found')

    log_entry_q = btc.DepositsLog.query\
        .filter_by(bitcoind_inst=bitcoind_inst)\
        .order_by(desc(btc.DepositsLog.timestamp))\
        .limit(1)

    try:
        log_entry = log_entry_q.one()
        latest_block_hash = log_entry.confirmed_block_hash
    except NoResultFound:
        latest_block_hash = ''
        # if update_amounts is True:
        #     affected_addresses_q = btc.Address.query.filter(
        #         btc.Address.bitcoind_inst == bitcoind_inst,
        #         btc.Address.is_populated.is_(True)
        #     )
        #
        #     affected_addresses = affected_addresses_q.all()
        #     for a in affected_addresses:
        #         a.amount = 0.0
        #
        #     sqla_session.flush()     # commit() is so early
        #     sqla_session.expunge_all()

    bitcoind = bitcoind_inst.get_rpc_conn()
    try:
        res = bitcoind.listsinceblock(latest_block_hash, confirmations, True)
    except JSONRPCException as e:
        raise BtcMonitorTransactionException(str(e)) from e

    txs = res['transactions']
    receive_txs = [x for x in txs if x['category'] == 'receive' and x['confirmations'] >= confirmations]

    txids = [x['txid'] for x in receive_txs]
    change_txs_q = btc.ChangeTransactionLog.query.filter(
        # Size of sql-statement is limited to 1G. It will be enough
        # See https://doxygen.postgresql.org/memutils_8h.html#a74a92b981e9b6aa591c5fbb24efd1dac
        btc.ChangeTransactionLog.change_tx_id.in_(txids)
    )
    change_txs = change_txs_q.all()
    change_txids = [x.change_tx_id for x in change_txs]

    addresses = defaultdict(decimal.Decimal)
    for t in receive_txs:
        if t['txid'] in change_txids:
            continue
        address = t['address']
        amount = t['amount']
        addresses[address] += amount

    involved_addresses_q = btc.Address.query.filter(
        # Size of sql-statement is limited to 1G. It will be enough
        # See https://doxygen.postgresql.org/memutils_8h.html#a74a92b981e9b6aa591c5fbb24efd1dac
        btc.Address.address.in_(addresses.keys()),
        btc.Address.bitcoind_inst == bitcoind_inst,
        btc.Address.is_populated.is_(True)
    )

    involved_addresses = involved_addresses_q.all()
    res_addresses = defaultdict(list)
    for a in involved_addresses:
        res_addresses[a.address].append(addresses[a.address])
        # if update_amounts is True:
        #     a.amount += addresses[a.address]

    lastblock = res['lastblock']
    check_lastblock_q = btc.DepositsLog.query.filter(
        btc.DepositsLog.confirmed_block_hash == lastblock,
        btc.DepositsLog.confirmations_applied == confirmations
    )
    try:
        check_lastblock_q.one()
    except NoResultFound:
        log_lastblock = btc.DepositsLog(
            bitcoind_inst=bitcoind_inst,
            confirmations_applied=confirmations,
            confirmed_block_hash=lastblock
        )
        sqla_session.add(log_lastblock)

    sqla_session.commit()

    return res_addresses


@_btc_dispatcher.add_method
def get_txid_status(bt_name, txid):
    try:
        bitcoind_inst = btc.BitcoindInstance.query.filter_by(instance_name=bt_name).one()
    except NoResultFound:
        raise BtcMonitorTransactionException(f'Bitcoind RPC server with name {bt_name} not found')

    bitcoind = bitcoind_inst.get_rpc_conn()
    try:
        res = bitcoind.gettransaction(txid)
    except JSONRPCException as e:
        raise BtcMonitorTransactionException(str(e)) from e

    return res
