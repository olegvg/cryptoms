import logging

from .utils import ExceptionBaseClass

generic_logger = logging.getLogger('.generic')
btc_logger = logging.getLogger('.btc')
eth_logger = logging.getLogger('.eth')


class DaemonConfigException(ExceptionBaseClass):
    logger = generic_logger


class BtcBaseClass(ExceptionBaseClass):
    logger = btc_logger


class EthBaseClass(ExceptionBaseClass):
    logger = eth_logger


class BtcAddressIntegrityException(BtcBaseClass):
    pass


class BtcAddressCreationException(BtcBaseClass):
    pass


class BtcAddressValidationException(BtcBaseClass):
    pass


class BtcCreateTransactionException(BtcBaseClass):
    pass


class BtcSignTransactionException(BtcBaseClass):
    pass


class BtcSendTransactionException(BtcBaseClass):
    pass


class BtcMonitorTransactionException(BtcBaseClass):
    pass


class EthAddressIntegrityException(EthBaseClass):
    pass


class EthAddressCreationException(EthBaseClass):
    pass


class EthMonitorTransactionException(EthBaseClass):
    pass


class TransactionInconsistencyError(ExceptionBaseClass):
    logger = generic_logger
