from transer.exceptions import BtcSendTransactionException
from bitcoinrpc.authproxy import JSONRPCException


def send_raw_transaction(bitcoind_inst, signed_trx_h):
    """
    create_raw_transaction()

    :param bitcoind_inst: instance of btc.BitcoindInstance
    :param signed_trx_h: signed raw transaction as hex:str
    :return: sent_trx -  отправленная транзакция в dict
    """

    bitcoind = bitcoind_inst.get_rpc_conn()
    try:
        txid = bitcoind.sendrawtransaction(signed_trx_h)
    except JSONRPCException as e:
        print(e)
        raise BtcSendTransactionException(str(e))

    return txid
