import secrets
from ethereum import utils
from transer.eth import _eth_dispatcher
from transer.exceptions import EthAddressIntegrityException


@_eth_dispatcher.add_method
def create_priv_keys(num_keys=1):
    """
    create_priv_keys()

    :param num_keys: number of keys to generate
    :return: `list` of `str` where `str` is hex-encoded private key
    """

    try:
        num_keys = int(num_keys)
    except TypeError:
        raise EthAddressIntegrityException(f'Argument is invalid')

    priv_keys = []
    for _ in range(0, num_keys):
        seed = secrets.token_hex(32)  # 256 bits of randomness
        priv_key_b = utils.sha3(seed)
        priv_key_hex = utils.encode_hex(priv_key_b)
        priv_keys.append(priv_key_hex)
    return priv_keys


@_eth_dispatcher.add_method
def create_keypairs(num_keypairs=1):
    """
    create_keypairs()

    :param num_keypairs: number of addrs/keys to generate
    :return: `dict` of {`str`: `str`} where `key` is hex-encoded ethereum address, `value` is hex-encoded private key
    """

    try:
        num_keypairs = int(num_keypairs)
    except TypeError:
        raise EthAddressIntegrityException(f'Argument is invalid')

    keypairs = {}
    for _ in range(0, num_keypairs):
        seed = secrets.token_hex(32)  # 256 bits of randomness
        priv_key_b = utils.sha3(seed)
        priv_key_hex = utils.encode_hex(priv_key_b)

        addr = utils.privtoaddr(priv_key_b)
        addr_hex = utils.decode_addr(addr)

        keypairs[addr_hex] = priv_key_hex
    return keypairs
