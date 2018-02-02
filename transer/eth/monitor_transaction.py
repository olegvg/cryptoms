from datetime import datetime, timezone
from collections import defaultdict
from math import floor

from web3 import Web3
from sqlalchemy import desc, asc
from sqlalchemy.orm import load_only
from sqlalchemy.orm.exc import NoResultFound

from transer.db import eth, sqla_session
from transer.exceptions import EthMonitorTransactionException
from transer.eth import eth_divider, _eth_dispatcher


def rewind_to_earleist_address(web3_url):
    earlest_address_q = eth.Address.query\
        .order_by(asc(eth.Address.timestamp))\
        .limit(1)
    try:
        earlest_address = earlest_address_q.one()
    except NoResultFound as e:
        raise EthMonitorTransactionException('No deposit addresses to monitor') from e

    provider = Web3.HTTPProvider(web3_url)
    web3_inst = Web3(provider)
    bottom_block = web3_inst.eth.getBlock('earliest')
    top_block = web3_inst.eth.getBlock('latest')

    target_timestamp = earlest_address.timestamp

    while True:
        bottom_block_num = bottom_block['number']
        top_block_num = top_block['number']

        if top_block_num - bottom_block_num == 1:
            return top_block

        middle_block_num = floor(bottom_block_num + (top_block_num - bottom_block_num) / 2)
        middle_block = web3_inst.eth.getBlock(middle_block_num)

        if middle_block['timestamp'] <= target_timestamp.timestamp():
            bottom_block = middle_block
        elif middle_block['timestamp'] > target_timestamp.timestamp():
            top_block = middle_block


@_eth_dispatcher.add_method
def get_recent_deposit_transactions(web3_url):
    """

    :param web3_url: web3 RPC url as str
    :return:
    """

    provider = Web3.HTTPProvider(web3_url)
    web3_inst = Web3(provider)

    log_entry_q = eth.DepositsLog.query\
        .order_by(desc(eth.DepositsLog.block_num))\
        .limit(1)

    try:
        log_entry = log_entry_q.one()
        bottom_block_num = log_entry.block_num
    except NoResultFound:
        bottom_block = rewind_to_earleist_address(web3_url)
        bottom_block_num = bottom_block['number']
        bottom_block_obj = eth.DepositsLog(
            block_num=bottom_block_num,
            block_hash=bottom_block['hash'],
            block_timestamp=datetime.fromtimestamp(bottom_block['timestamp'], timezone.utc)
        )
        sqla_session.add(bottom_block_obj)

    top_block = web3_inst.eth.getBlock('latest')
    top_block_num = top_block['number']

    if top_block_num == bottom_block_num:
        return

    top_block_obj = eth.DepositsLog(
        block_num=top_block_num,
        block_hash=top_block['hash'],
        block_timestamp=datetime.fromtimestamp(top_block['timestamp'], timezone.utc)
    )
    sqla_session.add(top_block_obj)

    addesses_q = eth.Address.query.options(load_only('address'))
    addresses = {a.address for a in addesses_q.all()}

    involved_adresses = defaultdict(list)

    for b in range(bottom_block_num, top_block_num+1):
        block = web3_inst.eth.getBlock(b, True)
        txs = block['transactions']
        confirmations = top_block['number'] - b
        for tx in txs:
            to = tx['to']
            if to is None:
                continue
            to = to.lower()

            if to in addresses:
                data = {
                    'tx_hash': tx['hash'],
                    'amount': tx['value'] / eth_divider,
                    'timestamp': block['timestamp'],
                    'confirmations': confirmations
                }
                involved_adresses[to].append(data)

    sqla_session.commit()

    return involved_adresses


@_eth_dispatcher.add_method
def get_transaction(web3_url, tx_hash):
    """
    Simple Eth.getTransaction() wrapper

    :param web3_url: web3 RPC url as str
    :param tx_hash: hash of transaction
    :return:
    """

    provider = Web3.HTTPProvider(web3_url)
    web3_inst = Web3(provider)

    res = web3_inst.eth.getTransaction(tx_hash)
    if res is None:
        raise EthMonitorTransactionException(f'Transaction with hash {tx_hash} is not found')

    tx = dict(res)
    latest_block = web3_inst.eth.blockNumber
    tx['confirmations'] = latest_block - res['blockNumber']

    return tx
