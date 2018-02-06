import decimal
from collections import defaultdict

from transer.exceptions import BtcMonitorTransactionException
from transer.btc import _btc_dispatcher
from transer.db import btc, sqla_session

from sqlalchemy.orm.exc import NoResultFound


@_btc_dispatcher.add_method
def reconcile_addresses(bt_name, enforce=False, confirmations=6):
    try:
        bitcoind_inst = btc.BitcoindInstance.query.filter_by(instance_name=bt_name).one()
    except NoResultFound:
        raise BtcMonitorTransactionException(f'Bitcoind RPC server with name {bt_name} not found')

    bitcoind = bitcoind_inst.get_rpc_conn()
    utxos = bitcoind.listunspent(confirmations, 999999999)

    unspent_addresses = defaultdict(decimal.Decimal)
    for u in utxos:
        unspent_addresses[u['address']] += u['amount']

    addresses_q = btc.Address.query\
        .join(btc.BitcoindInstance)\
        .filter(
            btc.BitcoindInstance.instance_name == bt_name,
            btc.Address.is_populated.is_(True)
        )

    addrs = addresses_q.all()

    if len(addrs) == 0:
        return {}

    if enforce is True:
        for addr in addrs:
            if addr.address in unspent_addresses:
                addr.amount = unspent_addresses[addr.address]
            else:
                addr.amount = decimal.Decimal(0.0)

        sqla_session.commit()

    return unspent_addresses
