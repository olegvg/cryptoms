from os import environ
from concurrent import futures
import asyncio
from aiohttp import web

from transer.utils import concurrent_fabric, init_db, dump_db_ddl, recreate_entire_database
from transer.exceptions import DaemonConfigException
from transer.btc import init_btc
from transer.eth import init_eth

from transer import outerface
from transer import config


def run(db_uri, listen_host, listen_port, workers,
        btc_masterkey_name, eth_masterkey_name,
        btcd_instance_name, etcd_instance_uri):

    config['eth_masterkey_name'] = eth_masterkey_name
    config['btc_masterkey_name'] = btc_masterkey_name

    config['etcd_instance_uri'] = etcd_instance_uri
    config['btcd_instance_name'] = btcd_instance_name

    async_loop = asyncio.get_event_loop()
    app = web.Application()

    init_db(db_uri)
    btc_dispatcher = init_btc()      # gather JSON-RPC interfaces of Bitcoin processor
    eth_dispatcher = init_eth()      # gather JSON-RPC interfaces of Ethereum processor

    executor = futures.ProcessPoolExecutor(max_workers=workers)
    handler_fabric = concurrent_fabric(executor)

    app.router.add_post('/btc', handler_fabric(btc_dispatcher))
    app.router.add_post('/eth', handler_fabric(eth_dispatcher))
    app.router.add_post('/claim-wallet-addr/{currency}', outerface.claim_wallet_addr_endpoint)
    app.router.add_post('/withdraw', outerface.withdraw_endpoint)
    app.router.add_post('/withdrawal-status/{u_txid}', outerface.withdrawal_status_endpoint)

    web.run_app(app, host=listen_host, port=listen_port, loop=async_loop)


def main():
    btc_masterkey_name = environ['T_BTC_MASTERKEY_NAME']
    eth_masterkey_name = environ['T_ETH_MASTERKEY_NAME']

    btcd_instance_name = environ['T_BTCD_INSTANCE_NAME']
    etcd_instance_uri = environ['T_ETCD_INSTANCE_URI']

    try:
        db_uri = environ['T_DB_URI']
        listen_host = environ['T_LISTEN_HOST']
        listen_port = int(environ['T_LISTEN_PORT'])
        workers = environ['WORKERS']
    except KeyError as e:
        raise DaemonConfigException("Config env vars don't set properly. Can't start.") from e

    run(
        db_uri=db_uri,
        listen_host=listen_host,
        listen_port=listen_port,
        workers=workers,
        btc_masterkey_name=btc_masterkey_name,
        eth_masterkey_name=eth_masterkey_name,
        btcd_instance_name=btcd_instance_name,
        etcd_instance_uri=etcd_instance_uri
    )


if __name__ == '__main__':
    run(
        db_uri='postgresql://ogaidukov@127.0.0.1:5432/btc_test',
        listen_host='127.0.0.1',
        listen_port=8000,
        workers=10,
        btc_masterkey_name='btc_main',
        eth_masterkey_name='eth_main',
        btcd_instance_name='main_instance',
        etcd_instance_uri=''
    )
