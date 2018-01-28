import logging

from .utils import ExceptionBaseClass

logger = logging.getLogger('.db')


class DaemonConfigException(ExceptionBaseClass):
    logger = logger


class BtcAddressIntegrityException(ExceptionBaseClass):
    logger = logger


class BtcAddressCreationException(ExceptionBaseClass):
    logger = logger


class BtcAddressValidationException(ExceptionBaseClass):
    logger = logger


class BtcCreateTransactionException(ExceptionBaseClass):
    logger = logger


class BtcSignTransactionException(ExceptionBaseClass):
    logger = logger


class BtcSendTransactionException(ExceptionBaseClass):
    logger = logger


class BtcMonitorTransactionException(ExceptionBaseClass):
    logger = logger


class EthAddressIntegrityException(ExceptionBaseClass):
    logger = logger


class EtcAddressCreationException(ExceptionBaseClass):
    logger = logger


class TransactionInconsistencyError(ExceptionBaseClass):
    logger = logger
