from datetime import datetime
import logging

from ethereum import utils as ethereum_utils
from mnemonic import Mnemonic
from sqlalchemy import Column, Integer, String, Unicode, DateTime, ForeignKey, UniqueConstraint, Numeric, desc
from sqlalchemy.orm import relationship
from sqlalchemy.sql import functions

from Crypto.Cipher import AES
from Crypto.Hash import SHA256

from transer import config
from transer.ethereum_utils import bip44
from transer.exceptions import EthAddressCreationException
from transer.ethereum_utils.utils import bytes_to_str, hex_str_to_bytes
from . import Base, sqla_session

logger = logging.getLogger('db')

schema_prefix = 'eth_'

DERIVATION_PATH = "44'/60'/0'/0"    # see EIP84


class MasterKey(Base):
    __tablename__ = 'master_keys'

    __table_args__ = (
        {'schema': schema_prefix + 'private'}
    )

    masterkey_name = Column(Unicode, unique=True)   # человеческое имя порождающего мастер-ключа BIP32
    seed_encrypted = Column(String(256), unique=True)
    seed_aet = Column(String(32), unique=True)
    seed_nonce = Column(String(32), unique=True)
    network_id = Column(Integer, default=1)

    def __init__(self, masterkey_name, seed, encryption_key='Snake oil', network_id=1):
        """

        :param masterkey_name: человеко-читаемое имя мастер-ключа, используется при инициализации демона
        :param seed: hex-encoded сид-энтропия для BIP32/BIP44 мастер-ключа. Обычно, получается так:
            seed_b = Mnemonic.to_seed('word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12')
            seed = utils.encode_hex(seed_b)
        :param encryption_key: симметричный ключ шифрования для seed
        :param network_id: id сети Ethereum
        """

        self.masterkey_name = masterkey_name
        encryption_key_b = encryption_key.encode('utf-8')
        seed_b = seed.encode('utf-8')

        crypt_key = SHA256.new(encryption_key_b).digest()

        cipher = AES.new(crypt_key, AES.MODE_GCM)
        ciphertext, tag = cipher.encrypt_and_digest(seed_b)
        self.seed_encrypted = bytes_to_str(ciphertext)
        self.seed_aet = bytes_to_str(tag)
        self.seed_nonce = bytes_to_str(cipher.nonce)

        self.network_id = network_id

    def get_seed(self):
        seed_encrypted = hex_str_to_bytes(self.seed_encrypted)
        seed_aet = hex_str_to_bytes(self.seed_aet)
        seed_nonce = hex_str_to_bytes(self.seed_nonce)

        crypt_key = SHA256.new(config['eth_crypt_key'].encode('utf_8')).digest()

        decipher = AES.new(crypt_key, AES.MODE_GCM, seed_nonce)
        seed_b = decipher.decrypt_and_verify(seed_encrypted, seed_aet)

        return seed_b

    @staticmethod
    def create_from_mnemonic(cls, masterkey_name, mnemonic):
        """

        :param cls: MasterKey class. Usually substituted automatically
        :param masterkey_name: Human-readable name of master key
        :param mnemonic: Mnemonic representation of key.
            Usually, there are 12 words taken from special dict and separated with spaces.
        :return:
        """
        seed = Mnemonic.to_seed(mnemonic)
        seed_h = ethereum_utils.encode_hex(seed)
        inst = cls(
            masterkey_name=masterkey_name,
            seed=seed_h
        )
        sqla_session.add(inst)
        sqla_session.commit()
        return inst


class Address(Base):
    __tablename__ = 'addresses'

    __table_args__ = (
        UniqueConstraint('masterkey_ref', 'crypto_path', 'crypto_number'),
        {'schema': schema_prefix + 'public'}
    )

    masterkey_ref = Column(ForeignKey(MasterKey.id), index=True, nullable=True)  # might be nullable because of perms
    masterkey = relationship(MasterKey, lazy='select')

    # see http://pycoin.readthedocs.io/en/latest/source/pycoin.key.html#pycoin.key.BIP32Node.BIP32Node.subkey_for_path
    # BIP32/44/49/141 deterministic key generating path e.g. 44'/60'/0'/0
    crypto_path = Column(String, nullable=False)

    # last component of key generating path e.g. for 66 it will be 44'/60'/0'/0/66
    crypto_number = Column(Integer)

    address = Column(String(42), index=True, unique=True)
    amount = Column(Numeric(precision=32, scale=24, asdecimal=True))

    timestamp = Column(DateTime(timezone=True), default=functions.now(), index=True)

    def get_priv_key(self):
        seed_b = ethereum_utils.decode_hex(self.masterkey.get_seed())
        bip44_masterkey = bip44.HDPrivateKey.master_key_from_seed(seed_b)

        path_key = bip44.HDKey.from_path(bip44_masterkey, self.crypto_path)[-1]

        key = bip44.HDKey.from_path(path_key, str(self.crypto_number))[-1]
        return key._key.to_hex()  # pylint: disable=W0212

    @classmethod
    def create_addresses(cls, masterkey, from_crypto_num, num_addrs,
                         crypto_path=DERIVATION_PATH, override_timestamp=False):
        """
        create_addresses()

        :param masterkey: sqla инстанс BIP44 мастер-ключа
        :param crypto_path: BIP32 путь криптования (базовая часть)
        :param from_crypto_num: BIP32 путь криптования (начальное значение изменяемой части)
        :param num_addrs: количество создаваемых адресов
        :param override_timestamp: форсировать произвольный timestamp (datetime.datetime) или False в случае now().
                ОПАСНО - bitcoind-у может поплохеть от сильно ранней даты, он же делает full scan по всему blockchain
                c указанного времени
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
            raise EthAddressCreationException(f'''trying to create existing
            addresses with {masterkey.pub_masterkey}:{crypto_path}/{from_crypto_num}-{from_crypto_num+num_addrs}''')

        seed = masterkey.get_seed()
        seed_b = ethereum_utils.decode_hex(seed)
        bip44_masterkey = bip44.HDPrivateKey.master_key_from_seed(seed_b)

        path_key = bip44.HDKey.from_path(bip44_masterkey, crypto_path)[-1]

        instances = []
        for k in range(from_crypto_num, from_crypto_num + num_addrs):
            key = bip44.HDKey.from_path(path_key, str(k))[-1]
            address = key.public_key.address()

            if isinstance(override_timestamp, datetime):
                instances.append(cls(
                    masterkey=masterkey,
                    crypto_path=crypto_path,
                    crypto_number=k,
                    timestamp=override_timestamp,
                    address=address,
                    amount=0.0)
                )
            else:
                instances.append(cls(
                    masterkey=masterkey,
                    crypto_path=crypto_path,
                    crypto_number=k,
                    address=address,
                    amount=0.0)
                )

        sqla_session.add_all(instances)
        sqla_session.commit()

        return instances

    @classmethod
    def create_next_address(cls, masterkey, crypto_path=DERIVATION_PATH, override_timestamp=False):
        """
        create_addresses()

        :param masterkey: sqla инстанс BIP32 мастер-ключа
        :param crypto_path: BIP32 путь криптования (базовая часть)
        :param override_timestamp: форсировать произвольный timestamp (datetime.datetime) или False в случае now().
        :return: list of sqla инстансов Address
        """
        interested_addrs_q = cls.query.filter(
            cls.masterkey == masterkey,
            cls.crypto_path == crypto_path,
        ).order_by(
            desc(cls.crypto_number)
        )

        latest_row = interested_addrs_q.first()
        if latest_row is None:
            crypto_number = 0
        else:
            crypto_number = latest_row.crypto_number + 1

        new_address = cls.create_addresses(
            masterkey=masterkey,
            crypto_path=crypto_path,
            from_crypto_num=crypto_number,
            num_addrs=1,
            override_timestamp=override_timestamp
        )[0]
        return new_address


class DepositsLog(Base):
    __tablename__ = 'deposits_log_records'

    __table_args__ = {
        'schema': schema_prefix + 'public'
    }
    block_num = Column(Integer, index=True)
    block_hash = Column(String(66), unique=True)
    block_timestamp = Column(DateTime(timezone=True), index=True)
