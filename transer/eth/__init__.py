import decimal
import os.path

from jsonrpc import Dispatcher

from transer.utils import bulk_importer

eth_divider = decimal.Decimal('1000000000000000000')    # one Wei divider

_eth_dispatcher = Dispatcher()


def init_eth():
    mypath = os.path.dirname(os.path.realpath(__file__))
    #bulk_importer(mypath)
    return _eth_dispatcher
