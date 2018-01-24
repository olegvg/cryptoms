from schematics import types
from schematics.models import Model

from .types import CryptoCurrency, WithdrawalStatus


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


class WithdrawalStatusResponse(Model):
    tx_id = types.UUIDType(required=True)
    status = types.StringType(required=True, choices=[x.value for x in WithdrawalStatus])
