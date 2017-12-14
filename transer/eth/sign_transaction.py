import rlp
from ethereum import transactions, utils

from transer.eth.validate_address import validate_addr_format
from transer.exceptions import EthAddressIntegrityException

from transer.eth import _eth_dispatcher


@_eth_dispatcher.add_method
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
    if not validate_addr_format(src_addr):
        raise EthAddressIntegrityException(f'Invalid source address {src_addr}')

    cmp_addr = utils.privtoaddr(priv_key)
    cmp_addr_h = utils.decode_addr(cmp_addr)
    orig_addr_h = utils.normalize_address(src_addr)
    if cmp_addr_h != orig_addr_h:
        raise EthAddressIntegrityException(f'Source address {src_addr} is not derived '
                                           f'from supplied private key')

    unsigned_tx = unsigned_tx_h.decode('hex')

    # unmarshall serialized transaction to Python object
    tx = rlp.decode(unsigned_tx, transactions.Transaction)

    tx.sign(
        key=priv_key,
        network_id=network_id
    )

    signed_tx_h = rlp.encode(tx).encode('hex')
    return signed_tx_h
