import os.path

from jsonrpc import Dispatcher

from transer.utils import bulk_importer, docstrings_from_dispatcher


_btc_dispatcher = Dispatcher()


def init_btc():
    mypath = os.path.dirname(os.path.realpath(__file__))
    #bulk_importer(mypath)
    return _btc_dispatcher


@_btc_dispatcher.add_method
def info():
    return docstrings_from_dispatcher(_btc_dispatcher)
