from concurrent import futures
from aiohttp import web

from transer.utils import concurrent_fabric, init_db
from transer.btc import init_btc
from transer.eth import init_eth


def init():
    app = web.Application()

    init_db('postgresql://ogaidukov@127.0.0.1:5432/btc_test')
    btc_dispatcher = init_btc()      # gather JSON-RPC interfaces of Bitcoin processor
    eth_dispatcher = init_eth()      # gather JSON-RPC interfaces of Ethereum processor

    executor = futures.ProcessPoolExecutor(max_workers=10)
    handler_fabric = concurrent_fabric(executor)

    app.router.add_post('/btc', handler_fabric(btc_dispatcher))
    app.router.add_post('/eth', handler_fabric(eth_dispatcher))

    web.run_app(app, port=8000)


if __name__ == '__main__':
    init()
