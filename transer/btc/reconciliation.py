from transer.exceptions import BtcMonitorTransactionException
from transer.btc import _btc_dispatcher
from transer.db import btc, sqla_session

from sqlalchemy.orm.exc import NoResultFound


@_btc_dispatcher.add_method
def reconcile_addresses(bt_name, enforce=False, confirmations=6):
    addresses_q = btc.Address.query\
        .join(btc.BitcoindInstance)\
        .filter(
            btc.BitcoindInstance.instance_name == bt_name,
            btc.Address.is_populated.is_(True)
        )

    addrs = addresses_q.all()

    if len(addrs) == 0:
        return

    try:
        bitcoind_inst = btc.BitcoindInstance.query.filter_by(instance_name=bt_name).one()
    except NoResultFound:
        raise BtcMonitorTransactionException(f'Bitcoind RPC server with name {bt_name} not found')

    bitcoind = bitcoind_inst.get_rpc_conn()

    actuals = {}
    for addr in addrs:
        amount = bitcoind.getreceivedbyaddress(addr.address, confirmations)
        actuals[addr.address] = amount
        if enforce is True:
            addr.amount = amount

    sqla_session.commit()

    return actuals
