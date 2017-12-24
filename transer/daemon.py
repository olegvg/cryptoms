from os import environ
from concurrent import futures
from aiohttp import web

from transer.utils import concurrent_fabric, init_db
from transer.exceptions import DaemonConfigException
from transer.btc import init_btc
from transer.eth import init_eth


def init(db_uri, listen_host, listen_port, workers):

    app = web.Application()

    init_db(db_uri)
    btc_dispatcher = init_btc()      # gather JSON-RPC interfaces of Bitcoin processor
    eth_dispatcher = init_eth()      # gather JSON-RPC interfaces of Ethereum processor

    executor = futures.ProcessPoolExecutor(max_workers=workers)
    handler_fabric = concurrent_fabric(executor)

    app.router.add_post('/btc', handler_fabric(btc_dispatcher))
    app.router.add_post('/eth', handler_fabric(eth_dispatcher))

    web.run_app(app, host=listen_host, port=listen_port)


def main():
    try:
        db_uri = environ['T_DB_URI']
        listen_host = environ['T_LISTEN_HOST']
        listen_port = environ['T_LISTEN_PORT']
        workers = environ['WORKERS']
    except KeyError as e:
        raise DaemonConfigException("Config env vars don't set properly. Can't start.") from e

    init(
        db_uri=db_uri,
        listen_host=listen_host,
        listen_port=listen_port,
        workers=workers
    )


if __name__ == '__main__':
    init(
        db_uri='postgresql://ogaidukov@127.0.0.1:5432/btc_test',
        listen_host='127.0.0.1',
        listen_port='8000',
        workers=10
    )
