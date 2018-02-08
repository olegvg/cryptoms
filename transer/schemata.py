from schematics import types
from schematics.models import Model

from .types import CryptoCurrency, WithdrawalStatus, DepositStatus


class ClaimWalletAddressResponse(Model):
    wallet_address = types.StringType(required=True)


class WithdrawRequest(Model):
    tx_id = types.UUIDType(required=True)
    wallet_addr = types.StringType(required=True)
    amount = types.DecimalType(required=True)
    currency = types.StringType(required=True, choices=[x.value for x in CryptoCurrency])


class WithdrawResponse(Model):
    tx_id = types.UUIDType(required=True)
    status = types.StringType(required=True, choices=[x.value for x in WithdrawalStatus])


class WithdrawCallbackRequest(Model):
    tx_id = types.UUIDType(required=True)
    status = types.StringType(required=True, choices=[x.value for x in WithdrawalStatus])


class DepositCallbackRequest(Model):
    tx_id = types.UUIDType(required=True)
    wallet_addr = types.StringType(required=True)
    amount = types.DecimalType(required=True)
    currency = types.StringType(required=True, choices=[c.value for c in CryptoCurrency])
    status = types.StringType(required=True, choices=[x.value for x in DepositStatus])
