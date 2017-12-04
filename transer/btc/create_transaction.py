import decimal

from .validate_addresses import validate_addrs
from ..exceptions import BtcCreateTransactionException


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


def raw_transaction_fee(bitcoind_inst, sources, destination, change=None, preferred_blocks=2):
    """
    Считалка рекомендованной комиссии транзакции в BTC
    Формула: bytes = 148 * in + 34 * out + 10 ± in

    :param sources: [wallet_address, ...], где wallet_address:str
    :param destination: wallet_address of str
    :param change: wallet_address of str - кошелек для остатка
    :param preferred_blocks: среднее время включения транзакции в чейн
        / количество блоков до включения транзакции в чейн
    :return: fee in BTC as decimal.Decimal
    """

    byte_size = raw_transaction_size(sources, destination, change)
    bitcoind = bitcoind_inst.get_rpc_conn()

    # Смотри https://github.com/bitcoin/bitcoin/issues/11500 и https://github.com/bitcoin/bitcoin/pull/10199
    # Для testnet не работает
    fee = bitcoind.estimatesmartfee(preferred_blocks)

    errors = fee.get('errors')
    if errors:
        e = ', '.join(errors)
        raise BtcCreateTransactionException(f'Fee calculation is impossible because of errors: {e}')

    return decimal.Decimal(fee['feerate']) / 1024.0 * byte_size


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
    txids = [j['txid'] for k in txs for j in k]
    utxos = [{'txid': i, 'vout': 0} for i in txids]

    outs = {destination: amount}
    if total > amount + fee:
        outs[change] = total - (amount + fee)

    bitcoind = bitcoind_inst.get_rpc_conn()
    trx_h = bitcoind.createrawtransaction(utxos, outs)
    trx = bitcoind.decoderawtransaction(trx_h)
    return trx_h, trx
