from .validate_addresses import addresses_to_insts
from transer.exceptions import BtcSignTransactionException


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
