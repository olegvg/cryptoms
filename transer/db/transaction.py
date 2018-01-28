import logging

from sqlalchemy import Column, String, DateTime, Numeric, Boolean
from sqlalchemy.sql import functions
from sqlalchemy.dialects.postgresql import UUID, ARRAY, ENUM

from transer import types

from . import Base


logger = logging.getLogger('db')

schema_prefix = 'common_'


class CryptoWithdrawTransaction(Base):
    __tablename__ = 'crypto_withdraw_transactions'

    __table_args__ = {
        'schema': schema_prefix + 'public'
    }

    u_txid = Column(UUID(as_uuid=True), unique=True)
    currency = Column(ENUM(*[x.value for x in types.CryptoCurrency], name='currency'))
    txids = Column(ARRAY(String))
    status = Column(ENUM(*[x.value for x in types.WithdrawalStatus],
                         name='crypto_withdraw_transaction_status'),
                    index=True)
    is_acknowledged = Column(Boolean, default=False)
    timestamp = Column(DateTime(timezone=True), default=functions.now(), index=True)


class CryptoDepositTransaction(Base):
    __tablename__ = 'crypto_deposit_transactions'

    __table_args__ = {
        'schema': schema_prefix + 'public'
    }

    u_txid = Column(UUID(as_uuid=True), unique=True)
    currency = Column(ENUM(*[x.value for x in types.CryptoCurrency], name='currency'), index=True)
    address = Column(String, index=True)
    txid = Column(String, index=True)
    amount = Column(Numeric(precision=32, scale=24, asdecimal=True))
    status = Column(ENUM(*[x.value for x in types.DepositStatus],
                         name='crypto_deposit_transaction_status'),
                    index=True)
    is_acknowledged = Column(Boolean, default=False)
    timestamp = Column(DateTime(timezone=True), default=functions.now(), index=True)
