import logging

from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import functions
from sqlalchemy.dialects.postgresql import UUID, ARRAY, ENUM

from transer.types import CryptoCurrency, WithdrawalStatus

from . import Base


logger = logging.getLogger('db')

schema_prefix = 'common_'


class CryptoTransaction(Base):
    __tablename__ = 'crypto_transactions'

    __table_args__ = {
        'schema': schema_prefix + 'public'
    }

    u_txid = Column(UUID(as_uuid=True), unique=True)
    currency = Column(ENUM(*[x.value for x in CryptoCurrency], name='currency'))
    txids = Column(ARRAY(String))
    status = Column(ENUM(*[x.value for x in WithdrawalStatus], name='crypto_transaction_status'))
    timestamp = Column(DateTime(timezone=True), default=functions.now(), index=True)
