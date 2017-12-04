import calendar
import functools
import logging

from sqlalchemy import Column, Integer, String, Unicode, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import functions

from pycoin.key.BIP32Node import BIP32Node

from bitcoinrpc.authproxy import AuthServiceProxy

from . import Base, sqla_session
from .exceptions import AddressIntegrityException, AddressCreationException

logger = logging.getLogger('db')

schema_prefix = 'btc_'


class MasterKey(Base):
    __tablename__ = 'master_keys'

    __table_args__ = (
        UniqueConstraint('priv_masterkey', 'pub_masterkey'),
        {'schema': schema_prefix + 'private'}
    )

    masterkey_name = Column(Unicode)   # человеческое имя порождающего мастер-ключа BIP32
    priv_masterkey = Column(String(111), unique=True)
    pub_masterkey = Column(String(111), unique=True)
    treat_as_testnet = Column(Boolean, default=False)

    def __init__(self, masterkey_name, priv_masterkey, treat_as_testnet):
        self.masterkey_name = masterkey_name
        self.priv_masterkey =priv_masterkey
        bip32_key = BIP32Node.from_hwif(priv_masterkey)
        self.pub_masterkey = bip32_key.hwif(as_private=False)
        self.treat_as_testnet = treat_as_testnet


class BitcoindInstance(Base):
    __tablename__ = 'bitcoind_instances'

    __table_args__ = {
        'schema': schema_prefix + 'public'
    }

    instance_name = Column(Unicode)
    hostname = Column(String)
    port = Column(Integer)
    rpc_user = Column(String)
    rpc_passwd = Column(String)
    is_https = Column(Boolean, default=False)

    def get_url(self):
        s = 's' if self.is_https else ''
        return f'http{s}://{self.rpc_user}:{self.rpc_passwd}@{self.hostname}:{self.port}'

    def get_rpc_conn(self):
        return AuthServiceProxy(self.get_url())


class Address(Base):
    __tablename__ = 'addresses'

    __table_args__ = (
        UniqueConstraint('masterkey_ref', 'crypto_path', 'crypto_number'),
        {'schema': schema_prefix + 'public'}
    )

    # unassociated in case of null
    bitcoind_inst_ref = Column(ForeignKey(BitcoindInstance.id), index=True, nullable=True)
    bitcoind_inst = relationship(BitcoindInstance, lazy='select')

    masterkey_ref = Column(ForeignKey(MasterKey.id), index=True, nullable=True)  # might be nullable because of perms
    masterkey = relationship(MasterKey, lazy='select')

    # see http://pycoin.readthedocs.io/en/latest/source/pycoin.key.html#pycoin.key.BIP32Node.BIP32Node.subkey_for_path
    # BIP32/44/49/141 deterministic key generating path e.g. 44'/1'/0'/0
    crypto_path = Column(String, nullable=False)

    # last component of key generating path e.g. for 66 it will be 44'/1'/0'/0/66
    crypto_number = Column(Integer)

    address = Column(String(35), index=True, unique=True)
    timestamp = Column(DateTime(timezone=True), default=functions.now(), index=True)
    is_populated = Column(Boolean, default=False)

    def check_integrity(self):
        masterkey = self.masterkey.priv_masterkey
        bip32_key = BIP32Node.from_hwif(masterkey)
        full_path = f'{self.crypto_path}/{self.crypto_number}'

        netcode = 'XTN' if self.masterkey.treat_as_testnet is True else 'BTC'
        bip32_key._netcode = netcode  # грязный хак чтобы обойти кривую генерацию ключей для testnet в Electrum

        derived_key = bip32_key.subkey_for_path(full_path)

        if derived_key.bitcoin_address() != self.address:
            AddressIntegrityException(f'Difference between calculated and stored addresses for id {self.id}')

    @classmethod
    def create_addresses(cls, bitcoind_inst, masterkey, crypto_path, from_crypto_num, num_addrs, check_integrity=False):
        """
        create_addresses()

        :param bitcoind_inst: sqla инстанс rpc-коннектора к bitcoind
        :param masterkey: sqla инстанс BIP32 мастер-ключа
        :param crypto_path: BIP32 путь криптования (базовая часть)
        :param from_crypto_num: BIP32 путь криптования (начальное значение изменяемой части)
        :param num_addrs: количество создаваемых адресов
        :param
        :return: list of sqla инстансов Address
        """
        interested_addrs_q = cls.query.filter(
            cls.masterkey == masterkey,
            cls.crypto_path == crypto_path,
            cls.crypto_number >= from_crypto_num,
            cls.crypto_number < from_crypto_num + num_addrs
        )

        exist_addrs = interested_addrs_q.count()
        if exist_addrs != 0:
            raise AddressCreationException(f'''trying to create existing 
            addresses with {masterkey.pub_masterkey}:{crypto_path}/{from_crypto_num}-{from_crypto_num+num_addrs}''')

        bip32_key = BIP32Node.from_hwif(masterkey.priv_masterkey)
        netcode = 'XTN' if masterkey.treat_as_testnet is True else 'BTC'
        print(masterkey.priv_masterkey, netcode)
        bip32_key._netcode = netcode  # грязный хак чтобы обойти кривую генерацию ключей для testnet в Electrum

        instances = []
        for k in range(from_crypto_num, from_crypto_num+num_addrs):
            full_path = f'{crypto_path}/{k}'
            print(full_path)
            key = bip32_key.subkey_for_path(full_path)
            address = key.bitcoin_address()

            instances.append(cls(
                masterkey=masterkey,
                crypto_path=crypto_path,
                crypto_number=k,
                address=address))

        sqla_session.add_all(instances)
        sqla_session.commit()

        committed_instances = interested_addrs_q.all()
        addrs = []

        for i in committed_instances:
            addr = {
                       'scriptPubKey': {
                           'address': i.address
                       },
                       'timestamp': calendar.timegm(i.timestamp.utctimetuple())
                   }
            addrs.append(addr)

        rpc_conn = bitcoind_inst.get_rpc_conn()
        try:
            res = rpc_conn.importmulti(addrs, {'rescan': True})
        except ConnectionRefusedError as e:
            logger.error(e)
            return None

        # poor man's способ узнать успешность importmulti :)
        success = functools.reduce(lambda x, y: x and y, [i['success'] for i in res])

        if success is True:
            cls.update_bitcoind_with_addresses(bitcoind_inst, committed_instances, check_integrity)
        return committed_instances

    @staticmethod
    def update_bitcoind_with_addresses(bitcoind_inst, instances, check_integrity=False):
        for i in instances:
            if check_integrity is True:
                i.check_integrity()
            i.is_populated = True
            i.bitcoind_inst = bitcoind_inst
        sqla_session.commit()
        return instances
