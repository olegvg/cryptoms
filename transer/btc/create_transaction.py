import decimal

from transer.btc.validate_addresses import validate_addrs
from transer.exceptions import BtcCreateTransactionException
from transer.btc import _btc_dispatcher
from transer.db.btc import BitcoindInstance

from sqlalchemy.orm.exc import NoResultFound


def raw_transaction_size(sources, destination, change=None):
    """
    Считалка размера транзакции в байтах
    Формула: bytes = 148 * in + 34 * out + 10 ± in

    :param sources: [wallet_address, ...], где wallet_address:str
    :param destination: wallet_address of str
    :param change: wallet_address of str - кошелек для остатка
    :return: ожидаемое количество байт в транзакции
    """

    if not isinstance(sources, (list, set, tuple)):
        return None
    else:
        ins = len(sources)

    if not isinstance(destination, str):
        return None
    outs = 1

    if isinstance(change, str):
        outs += 1

    return 148 * ins + 34 * outs + 10


def transaction_fee_per_byte(bitcoind_inst, preferred_blocks=2):
    bitcoind = bitcoind_inst.get_rpc_conn()

    # Смотри https://github.com/bitcoin/bitcoin/issues/11500 и https://github.com/bitcoin/bitcoin/pull/10199
    # Для testnet не работает
    fee = bitcoind.estimatesmartfee(preferred_blocks)
    return fee


def raw_transaction_fee(bitcoind_inst, sources, destination, change=None, preferred_blocks=2):
    """
    Считалка рекомендованной комиссии транзакции в BTC для P2SH-транзакции
    Формула: bytes = 148 * in + 34 * out + 10 ± in

    :param bitcoind_inst: instance of btc.BitcoindInstance
    :param sources: [wallet_address, ...], где wallet_address:str
    :param destination: wallet_address of str
    :param change: wallet_address of str - кошелек для остатка
    :param preferred_blocks: среднее время включения транзакции в чейн
        / количество блоков до включения транзакции в чейн
    :return: fee in BTC as decimal.Decimal
    """

    byte_size = raw_transaction_size(sources, destination, change)
    fee = transaction_fee_per_byte(
        bitcoind_inst=bitcoind_inst,
        preferred_blocks=preferred_blocks
    )

    errors = fee.get('errors')
    if errors:
        e = ', '.join(errors)
        raise BtcCreateTransactionException(f'Fee calculation is impossible because of errors: {e}')

    # kilobyte == 1000 bytes ^__^       https://en.wikipedia.org/wiki/Kilobyte
    return byte_size * fee['feerate'] / decimal.Decimal(1000.0)


def create_raw_transaction(bitcoind_inst, sources, destination,
                           amount, change=None, fee=decimal.Decimal(0), confirmations=6):
    """
    create_raw_transaction()

    :param bitcoind_inst: instance of btc.BitcoindInstance
    :param sources: [wallet_address, ...], где wallet_address:str
    :param destination: wallet_address as str
    :param amount: объём средств к перечислению; decimal.Decimal
    :param change: wallet_address as str - кошелек для остатка или None
    :param fee: комиссия за транзакцию, не более указанного; decimal.Decimal
    :param confirmations: количество подтвержденных блоков для засчитывания транзакции
    :return: (trx_h, trx) -  сырая транзакция в hex:str и декодированная транзакция в dict
    """

    detailed_srcs, total, status = validate_addrs(
        bitcoind_inst=bitcoind_inst,
        addresses=sources,
        estimate_spendables=amount + fee,
        confirmations=confirmations

    )

    if status is not True:
        raise BtcCreateTransactionException(f'insufficient amount of funds in sources {sources}')

    txs = [i['txids'] for i in detailed_srcs.values()]
    utxos = [{'vout': j['vout'], 'txid': j['txid']} for k in txs for j in k]

    outs = {destination: amount}
    if total > amount + fee:
        outs[change] = total - (amount + fee)

    bitcoind = bitcoind_inst.get_rpc_conn()
    trx_h = bitcoind.createrawtransaction(utxos, outs)
    trx = bitcoind.decoderawtransaction(trx_h)
    return trx_h, trx


@_btc_dispatcher.add_method
def calculate_transaction_fee(bt_name, sources, destination, change=None, preferred_blocks=2):
    """
    `calculate_transaction_fee()`

    Калькулятор рекомендованной комиссии транзакции в BTC для P2SH-транзакции
    Формула: bytes = 148 * in + 34 * out + 10 ± in

    :param bt_name: name to lookup in btc.BitcoindInstance, as str
    :param sources: [wallet_address, ...], где wallet_address:str
    :param destination: wallet_address of str
    :param change: wallet_address of str - кошелек для остатка
    :param preferred_blocks: среднее время включения транзакции в чейн
        / количество блоков до включения транзакции в чейн
    :return: fee in BTC as decimal.Decimal
    """

    try:
        bt_name = str(bt_name)
        sources = list(sources)
        destination = str(destination)
        change = str(change) if change is not None else None
        preferred_blocks = int(preferred_blocks)
    except TypeError:
        raise BtcCreateTransactionException(f'One of arguments is invalid')

    try:
        bitcoind_inst = BitcoindInstance.query.filter_by(instance_name=bt_name).one()
    except NoResultFound:
        raise BtcCreateTransactionException(f'Bitcoind RPC server with name {bt_name} not found')

    return raw_transaction_fee(
        bitcoind_inst=bitcoind_inst,
        sources=sources,
        destination=destination,
        change=change,
        preferred_blocks=preferred_blocks
    )


@_btc_dispatcher.add_method
def create_transaction(bt_name, sources, destination, amount, change=None, fee='0', confirmations=6):
    """
    `create_transaction()`

    Создаватель сырой транзакции

    :param bt_name: name to lookup in btc.BitcoindInstance, as str
    :param sources: [wallet_address, ...], где wallet_address:str
    :param destination: wallet_address as str
    :param amount: объём средств к перечислению as str
    :param change: wallet_address as str - кошелек для остатка или None
    :param fee: комиссия за транзакцию, не более указанного as str
    :param confirmations: количество подтвержденных блоков для засчитывания транзакции
    :return: (trx_h, trx) -  сырая транзакция в hex:str и декодированная транзакция в dict
    """

    try:
        bt_name = str(bt_name)
        sources = list(sources)
        destination = str(destination)
        amount = decimal.Decimal(str(amount))
        change = str(change) if change is not None else None
        fee = decimal.Decimal(str(fee))
        confirmations = int(confirmations)
    except (TypeError, decimal.InvalidOperation):
        raise BtcCreateTransactionException(f'One of arguments is invalid')

    try:
        bitcoind_inst = BitcoindInstance.query.filter_by(instance_name=bt_name).one()
    except NoResultFound:
        raise BtcCreateTransactionException(f'Bitcoind RPC server with name {bt_name} not found')

    return create_raw_transaction(
        bitcoind_inst=bitcoind_inst,
        sources=sources,
        destination=destination,
        amount=amount,
        change=change,
        fee=fee,
        confirmations=confirmations
    )
