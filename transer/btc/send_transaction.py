from bitcoinrpc.authproxy import JSONRPCException

from transer.btc import _btc_dispatcher
from transer.db.btc import BitcoindInstance
from transer.exceptions import BtcSendTransactionException

from sqlalchemy.orm.exc import NoResultFound


def send_raw_transaction(bitcoind_inst, signed_trx_h):
    """
    send_raw_transaction()

    :param bitcoind_inst: instance of btc.BitcoindInstance
    :param signed_trx_h: signed raw transaction as hex:str
    :return: sent_txid -  txid отправленной транзакции
    """

    bitcoind = bitcoind_inst.get_rpc_conn()
    try:
        txid = bitcoind.sendrawtransaction(signed_trx_h)
    except JSONRPCException as e:
        print(e)
        raise BtcSendTransactionException(str(e))

    return txid


@_btc_dispatcher.add_method
def send_transaction(bt_name, signed_trx):
    """
    send_transaction()

    :param bt_name: name to lookup in btc.BitcoindInstance, as str
    :param signed_trx: signed raw transaction as hex:str
    :return: sent_txid -  txid отправленной транзакции
    """

    try:
        bt_name = str(bt_name)
        signed_trx = str(signed_trx)
    except TypeError:
        raise BtcSendTransactionException(f'One of arguments is invalid')

    try:
        bitcoind_inst = BitcoindInstance.query.filter_by(instance_name=bt_name).one()
    except NoResultFound:
        raise BtcSendTransactionException(f'Bitcoind RPC server with name {bt_name} not found')

    return send_raw_transaction(
        bitcoind_inst=bitcoind_inst,
        signed_trx_h=signed_trx
    )
