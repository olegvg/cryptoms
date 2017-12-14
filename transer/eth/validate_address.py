import decimal

from ethereum import utils
from web3 import Web3

from transer.exceptions import EthAddressIntegrityException
from transer.eth import eth_divider, _eth_dispatcher


@_eth_dispatcher.add_method
def validate_addr_format(addr):
    """

    :param addr: hex-encoded address as str
    :return: True/False whether address checksum is or or not. Else raise EthAddressIntegrityException exception
    """
    try:
        return utils.check_checksum(addr)
    except Exception as e:
        raise EthAddressIntegrityException(e)


@_eth_dispatcher.add_method
def validate_existence_addr(web3_url, addr, estimate_spendable=decimal.Decimal(0)):
    """
    Простая валидация адреса: присутствие транзакций в чейне с участием этого адреса и достаточность средств.
    Так как в чейн эфира устроен иначе (нет txid и UTXOs), то проверка адреса сводится к серии RPC вызовов,
    а валидность полностью ложится на geth/parity/smt else.
    См. https://ethereum.github.io/yellowpaper/paper.pdf #6, #10, #11.1 (block height взят всё тот же 6 от верха)
    :param web3_url: web3 RPC url as str
    :param addr: интересуемый hex-encoded адрес as str
    :param estimate_spendable: достаточность средств на адресе as Decimal, приведенный к 1 Эфиру
        i.e. divided by Wei
    :return: True/False - достаточно или нет средств; None если по адресу нет транзакций
    """
    provider = Web3.HTTPProvider(web3_url)
    web3_inst = Web3(provider)

    validate_existence_addr_(
        web3_inst=web3_inst,
        addr=addr,
        estimate_spendable=estimate_spendable
    )


def validate_existence_addr_(web3_inst, addr, estimate_spendable=decimal.Decimal(0)):
    if validate_addr_format(addr) is not True:
        raise EthAddressIntegrityException(f'addr {addr} seems to be invalid')
    transactions = web3_inst.eth.getTransactionCount(addr)
    if transactions == 0:
        return None
    balance = web3_inst.eth.getBalance(addr)
    balance /= eth_divider  # convert to Ethers
    return balance >= estimate_spendable