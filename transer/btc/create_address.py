import functools
import calendar

from transer.exceptions import BtcAddressIntegrityException
from transer.btc import _btc_dispatcher
from transer.db import sqla_session
from transer.db.btc import BitcoindInstance, Address, MasterKey

from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from transer import config
from transer.utils import jsonrpc_caller

btc_signing_instance_uri = config['btc_signing_instance_uri']


@_btc_dispatcher.add_method
@jsonrpc_caller(target_uri=btc_signing_instance_uri, catchables=[BtcAddressIntegrityException])
def create_unpropagated_address(bt_name, key_name):
    try:
        bt_name = str(bt_name)
        key_name = str(key_name)
    except TypeError:
        raise BtcAddressIntegrityException(f'One of arguments is invalid')

    try:
        bitcoind_inst = BitcoindInstance.query.filter_by(instance_name=bt_name).one()
    except NoResultFound as e:
        raise BtcAddressIntegrityException(f'Bitcoind RPC server with name {bt_name} not found') from e

    try:
        masterkey = MasterKey.query.filter(
            MasterKey.masterkey_name == key_name
        ).one()
    except (NoResultFound, MultipleResultsFound) as e:
        raise BtcAddressIntegrityException(f'Masterkey lookup finished up with error') from e

    address_row = Address.create_next_address(
        bitcoind_inst=bitcoind_inst,
        masterkey=masterkey,
        update_bitcoind=False  # NB!
    )

    return address_row.address


@_btc_dispatcher.add_method
def propdagate_bitcoind_with_address(bt_name, address):
    try:
        bt_name = str(bt_name)
        address = str(address)
    except TypeError:
        raise BtcAddressIntegrityException(f'One of arguments is invalid')

    try:
        bitcoind_inst = BitcoindInstance.query.filter_by(instance_name=bt_name).one()
    except NoResultFound as e:
        raise BtcAddressIntegrityException(f'Bitcoind RPC server with name {bt_name} not found') from e

    try:
        addr_inst = Address.query.filter_by(bitcoind_inst=bitcoind_inst, address=address).one()
    except NoResultFound as e:
        raise BtcAddressIntegrityException(f'{address} is not found/tied to {bitcoind_inst.instance_name}') from e

    addr_obj = {
        'scriptPubKey': {'address': address},
        'timestamp': calendar.timegm(addr_inst.timestamp.utctimetuple())
    }

    rpc_conn = bitcoind_inst.get_rpc_conn()
    try:
        res = rpc_conn.importmulti([addr_obj], {'rescan': True})
    except ConnectionRefusedError as e:
        raise BtcAddressIntegrityException('Connection to bitcoind refused') from e

    # poor man's способ узнать успешность importmulti :)
    success = functools.reduce(lambda x, y: x and y, [i['success'] for i in res])

    if not success:
        raise BtcAddressIntegrityException(f'bitcoind importmulti() unsuccessful for {address}')

    addr_inst.is_populated = True
    sqla_session.commit()
