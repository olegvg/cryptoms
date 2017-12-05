import os.path

from jsonrpc import Dispatcher

from transer.utils import bulk_importer


_btc_dispatcher = Dispatcher()


def init_btc():
    mypath = os.path.dirname(os.path.realpath(__file__))
    bulk_importer(mypath)
    return _btc_dispatcher
