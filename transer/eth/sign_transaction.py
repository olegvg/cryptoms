import codecs

import rlp
from ethereum import transactions, utils

from transer.eth.validate_address import normalize_addr
from transer.exceptions import EthAddressIntegrityException
from transer.eth import _eth_dispatcher
from transer import config
from transer.utils import jsonrpc_caller

eth_signing_instance_uri = config['eth_signing_instance_uri']


@_eth_dispatcher.add_method
@jsonrpc_caller(target_uri=eth_signing_instance_uri, catchables=[EthAddressIntegrityException])
def sign_transaction(src_addr, priv_key, unsigned_tx_h, network_id=1):
    """
    sign_transaction()

    :param src_addr: source address as hex str
    :param priv_key: private key corresponding to source address as hex str
    :param unsigned_tx_h: unsigned transaction as hex str
    :param network_id: номер нетворка: 1=Frontier, 2=Morden (disused), 3=Ropsten, 4=Rinkeby, see current state at
        https://github.com/ethereum/go-ethereum/blob/46e5583993afe7b9d0ff432f846b2a97bcb89876/cmd/utils/flags.go#L130
    :return: signed transaction as hex str
    """
    src_addr = normalize_addr(src_addr)

    cmp_addr = utils.privtoaddr(priv_key)
    cmp_addr_h = '0x' + utils.decode_addr(cmp_addr)
    if cmp_addr_h != src_addr:
        raise EthAddressIntegrityException(f'Source address {src_addr} is not derived '
                                           f'from supplied private key')

    unsigned_tx = codecs.decode(unsigned_tx_h, 'hex')

    # unmarshall serialized transaction to Python object
    tx_obj = rlp.decode(unsigned_tx, transactions.Transaction)
    tx_obj.make_mutable()

    tx_obj.sign(
        key=priv_key,
        network_id=network_id
    )

    signed_tx_h = codecs.encode(rlp.encode(tx_obj, transactions.Transaction), 'hex')
    return '0x' + signed_tx_h.decode('ascii')
