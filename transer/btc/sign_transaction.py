from transer.btc.validate_addresses import addresses_to_insts
from transer.exceptions import BtcSignTransactionException
from transer.btc import _btc_dispatcher
from transer.db.btc import BitcoindInstance

from sqlalchemy.orm.exc import NoResultFound

# from transer import config
from transer.utils import jsonrpc_caller

# btc_signing_instance_uri = config['btc_signing_instance_uri']


def sign_raw_transaction(bitcoind_inst, signing_addrs, trx_h):
    """
    create_raw_transaction()

    :param bitcoind_inst: instance of btc.BitcoindInstance
    :param signing_addrs: [wallet_address, ...], где wallet_address:str - адреса, приватными ключами
        которых будет подписана транзакция
    :param trx_h: raw transaction as hex:str
    :return: (signed_trx_h, signed_trx) -  подписанные сырая транзакция в hex:str и декодированная транзакция в dict
    """

    signing_insts = addresses_to_insts(
        bitcoind_inst=bitcoind_inst,
        addresses=signing_addrs
    )

    private_keys = [i.get_priv_key() for i in signing_insts]

    bitcoind = bitcoind_inst.get_rpc_conn()
    signed_res = bitcoind.signrawtransaction(trx_h, None, private_keys)

    errors = signed_res.get('errors')
    if errors is not None:
        msg = ', '.join([f'{e["error"]} for {e["txid"]}' for e in errors])
        raise BtcSignTransactionException(msg)

    signed_trx_h = signed_res['hex']
    signed_trx = bitcoind.decoderawtransaction(signed_trx_h)

    return signed_trx_h, signed_trx


@_btc_dispatcher.add_method
# @jsonrpc_caller(target_uri=btc_signing_instance_uri, catchables=[Exception, KeyError])
def sign_transaction(bt_name, signing_addrs, trx):
    """
    sign_transaction()

    :param bt_name: name to lookup in btc.BitcoindInstance, as str
    :param signing_addrs: [wallet_address, ...], где wallet_address:str - адреса, приватными ключами
        которых будет подписана транзакция
    :param trx: raw transaction as hex:str
    :return: (signed_trx_h, signed_trx) -  подписанные сырая транзакция в hex:str и декодированная транзакция в dict
    """

    try:
        bt_name = str(bt_name)
        signing_addrs = list(signing_addrs)
        trx = str(trx)
    except TypeError:
        raise BtcSignTransactionException(f'One of arguments is invalid')

    try:
        bitcoind_inst = BitcoindInstance.query.filter_by(instance_name=bt_name).one()
    except NoResultFound:
        raise BtcSignTransactionException(f'Bitcoind RPC server with name {bt_name} not found')

    return sign_raw_transaction(
        bitcoind_inst=bitcoind_inst,
        signing_addrs=signing_addrs,
        trx_h=trx
    )
