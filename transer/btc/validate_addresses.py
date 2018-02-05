import decimal
import functools
from collections import defaultdict

from transer.exceptions import BtcAddressValidationException
from transer.db.btc import Address, BitcoindInstance
from transer.btc import _btc_dispatcher

from sqlalchemy.orm.exc import NoResultFound


def addresses_to_insts(bitcoind_inst, addresses):
    """

    :param bitcoind_inst: instance of btc.BitcoindInstance
    :param addresses: [wallet_address, ...], где wallet_address:str
    :return: [btc.Address(), ...]
    """
    interested_addrs_q = Address.query.filter(
        Address.address.in_(addresses),
        Address.is_populated.is_(True)
    )
    interested_addrs = interested_addrs_q.all()

    if len(interested_addrs) != len(addresses):
        raise BtcAddressValidationException(f'Not all requested addresses '
                                            f'are populated to {bitcoind_inst.instance_name}')
    return interested_addrs


def validate_addrs(bitcoind_inst, addresses, confirmations=6,
                   estimate_spendables=decimal.Decimal(0)):
    """
    validate_addrs()

    :param bitcoind_inst: instance of btc.BitcoindInstance
    :param addresses: [wallet_address, ...], где wallet_address:str
    :param confirmations: количество подтвержденных блоков для засчитывания транзакции
    :param estimate_spendables: количество BTC которое должно быть как минимум доступно в addresses
    :return: (interested_sources, total, status), где
        interested_sources - структуры для адресов из addresses + ['address_inst'] объекты db.btc.Address,
            по которым есть UXTOs
        total - сумма средств на UXTOs для адресов из addresses
        status - достаточность средств, True/False
    """

    interested_addrs = addresses_to_insts(
        bitcoind_inst=bitcoind_inst,
        addresses=addresses
    )

    bitcoind = bitcoind_inst.get_rpc_conn()

    res = bitcoind.listunspent(confirmations, 999999999, addresses)
    sources = defaultdict(dict)
    for i in res:
        addr = i['address']
        txid = i['txid']
        vout = i['vout']
        amount = i['amount']

        if addr not in sources.keys():
            for a in interested_addrs:
                if a.address == addr:
                    sources[addr]['address_inst'] = a

        txids = sources[addr].get('txids', list())
        txids.append({'txid': txid, 'amount': amount, 'vout': vout})
        sources[addr]['txids'] = txids

    txs = [i['txids'] for i in sources.values()]
    amounts = [j['amount'] for k in txs for j in k]
    try:
        total = functools.reduce(lambda x, y: x + y, amounts)
    except TypeError:
        total = decimal.Decimal(0.0)

    return sources, total, total >= estimate_spendables


@_btc_dispatcher.add_method
def validate_addresses(bt_name, addresses, confirmations=6, estimate_spendables=decimal.Decimal(0)):
    """
    validate_addresses()

    :param bt_name: name to lookup in btc.BitcoindInstance, as str
    :param addresses: [wallet_address, ...], где wallet_address:str
    :param confirmations: количество подтвержденных блоков для засчитывания транзакции
    :param estimate_spendables: количество BTC которое должно быть как минимум доступно в addresses
    :return: (interested_sources, total, status), где
        interested_sources - структуры для адресов из addresses, по которым есть UXTOs
        total - сумма средств на UXTOs для адресов из addresses
        status - достаточность средств, True/False
    """
    try:
        bt_name = str(bt_name)
        addresses = list(addresses)
        confirmations = int(confirmations)
        estimate_spendables = decimal.Decimal(estimate_spendables)
    except (TypeError, decimal.InvalidOperation):
        raise BtcAddressValidationException(f'One of arguments is invalid')

    try:
        bitcoind_inst = BitcoindInstance.query.filter_by(instance_name=bt_name).one()
    except NoResultFound:
        raise BtcAddressValidationException(f'Bitcoind RPC server with name {bt_name} not found')

    (interested_sources, total, status) = validate_addrs(
        bitcoind_inst=bitcoind_inst,
        addresses=addresses,
        confirmations=confirmations,
        estimate_spendables=estimate_spendables
    )

    # удаляем лишнее
    for addr in interested_sources.keys():
        del interested_sources[addr]['address_inst']

    return interested_sources, str(total), status
