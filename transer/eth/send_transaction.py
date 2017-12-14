from web3 import Web3

from transer.eth import _eth_dispatcher


@_eth_dispatcher.add_method
def send_transaction(web3_url, signed_tx_h):
    """
    send_transaction()

    :param web3_url: web3 RPC url as str
    :param signed_tx_h: signed transaction as hex str
    :return: transaction hash as str or None,
        for details, see https://github.com/ethereum/wiki/wiki/JSON-RPC#eth_sendrawtransaction
    """
    provider = Web3.HTTPProvider(web3_url)
    web3_inst = Web3(provider)

    res = web3_inst.eth.sendRawTransaction(signed_tx_h)
    if res:
        return res
    else:
        return None


@_eth_dispatcher.add_method
def transaction_receipt(web3_url, tx_hash):
    """
    transaction_receipt()

    :param web3_url: web3 RPC url as str
    :param tx_hash: transaction hash as hex str
    :return: transaction receipt as dict or None,
        for details, see https://github.com/ethereum/wiki/wiki/JSON-RPC#eth_gettransactionreceipt
    """
    provider = Web3.HTTPProvider(web3_url)
    web3_inst = Web3(provider)

    return web3_inst.eth.getTransactionReceipt(tx_hash)


@_eth_dispatcher.add_method
def current_block_number(web3_url):
    """
    current_block_number() - номер последнего блока в чейне

    :param web3_url: web3 RPC url as str
    :return: current block number
    """
    provider = Web3.HTTPProvider(web3_url)
    web3_inst = Web3(provider)
    return web3_inst.eth.blockNumber


@_eth_dispatcher.add_method
def check_transaction_mined(web3_url, tx_hash, blocks_depth=6):
    """
    transaction_receipt()

    :param web3_url: web3 RPC url as str
    :param tx_hash: transaction hash as hex str
    :param blocks_depth: number of blocks mined since transaction denoted by 'tx_hash' applied
    :return: True if there are at least 'blocks_depth' blocks mined since
        transaction denoted by 'tx_hash' applied, False otherwise
    """
    provider = Web3.HTTPProvider(web3_url)
    web3_inst = Web3(provider)

    receipt = web3_inst.eth.getTransactionReceipt(tx_hash)
    if receipt is None:
        return None

    mined_block_num = receipt['blockNumber']
    current_block_num = web3_inst.eth.blockNumber

    return mined_block_num + blocks_depth <= current_block_num
