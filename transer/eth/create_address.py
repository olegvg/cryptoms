from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from transer.exceptions import EthAddressIntegrityException
from transer.eth import _eth_dispatcher
from transer import config
from transer.utils import jsonrpc_caller

from transer.db import eth

eth_signing_instance_uri = config['eth_signing_instance_uri']


@_eth_dispatcher.add_method
@jsonrpc_caller(target_uri=eth_signing_instance_uri, catchables=[EthAddressIntegrityException])
def create_address():
    key_name = config.get('eth_masterkey_name', None)
    if key_name is None:
        raise EthAddressIntegrityException('eth_masterkey_name config option not found') from e

    masterkey_q = eth.MasterKey.query.filter(
        eth.MasterKey.masterkey_name == key_name
    )
    try:
        masterkey = masterkey_q.one()
    except (NoResultFound, MultipleResultsFound) as e:
        raise EthAddressIntegrityException('Error with masterkey. See traceback for details') from e

    newborn_address = eth.Address.create_next_address(masterkey=masterkey)
    return newborn_address.address
