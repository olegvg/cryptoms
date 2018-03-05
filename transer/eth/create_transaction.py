import decimal
import codecs

import rlp
from ethereum import transactions
from web3 import Web3

from transer.eth.validate_address import normalize_addr, validate_existence_addr_
from transer.exceptions import EthAddressIntegrityException

from transer.eth import eth_divider, _eth_dispatcher

# constant, amount of gas to run a transaction
# https://ethereum.github.io/yellowpaper/paper.pdf Appendix G
TRANSACTION_GAS = 21000


@_eth_dispatcher.add_method
def current_gas_price(web3_url):
    """
    current_gas_price()

    :param web3_url: web3 RPC url as str
    :return: current price of gas, in Ether (!)
    """
    provider = Web3.HTTPProvider(web3_url)
    web3_inst = Web3(provider)
    gas_price = web3_inst.eth.gasPrice
    return gas_price / eth_divider


@_eth_dispatcher.add_method
def create_transaction(web3_url, src_addr, dst_addr, amount, gas_price):
    """
    create_transaction()

    :param web3_url: web3 RPC url as str
    :param src_addr: source address as hex str
    :param dst_addr: destination address as hex str
    :param amount: amount of funds to transfer, in Ether (!) as str or float (may lead to imprecision)
    :param gas_price: price of gas, in Ether (!) as str or float (may lead to imprecision)
    :return: unsigned transaction as hex str
    """

    provider = Web3.HTTPProvider(web3_url)
    web3_inst = Web3(provider)

    amount = decimal.Decimal(amount) * eth_divider          # convert to Wei
    gas_price = decimal.Decimal(gas_price) * eth_divider    # convert to Wei
    fee = gas_price * TRANSACTION_GAS

    src_addr = normalize_addr(src_addr)

    # берём nonce тут, чтобы использовать его как optimistic lock для создаваемой транзакции
    nonce = web3_inst.eth.getTransactionCount(src_addr)

    if validate_existence_addr_(
            web3_inst=web3_inst,
            addr=src_addr,
            estimate_spendable=(amount + fee) / eth_divider  # convert back to Eth
    ) is not True:
        raise EthAddressIntegrityException(f'No enough Ether on source address {src_addr} '
                                           f'to perform the transaction')

    dst_addr = normalize_addr(dst_addr)

    tx = transactions.Transaction(
        nonce=nonce,
        gasprice=int(gas_price.to_integral_exact()),
        startgas=TRANSACTION_GAS,
        to=dst_addr,
        value=int(amount.to_integral_exact()),
        data=''
    )

    unsigned_tx_h = codecs.encode(rlp.encode(tx), 'hex')
    return unsigned_tx_h.decode()
