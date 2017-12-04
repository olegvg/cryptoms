import logging

from ..utils import ExceptionBaseClass

logger = logging.getLogger('.db')


class AddressIntegrityException(ExceptionBaseClass):
    logger = logger


class AddressCreationException(ExceptionBaseClass):
    logger = logger

