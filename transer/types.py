from enum import Enum


class CryptoCurrency(Enum):
    BITCOIN = 'BTC'
    ETHERIUM = 'ETH'


class DepositStatus(Enum):
    PENDING = 'PENDING'
    COMPLETED = 'COMPLETED'
    CANCELLED = 'CANCELLED'


class WithdrawalStatus(Enum):
    PREPENDING = 'PREPENDING'

    PENDING = 'PENDING'
    COMPLETED = 'COMPLETED'
    CANCELLED = 'CANCELLED'

    COMPLETED_CHARGED = 'COMPLETED_CHARGED'
