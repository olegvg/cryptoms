from datetime import datetime
import decimal
import unittest

from transer import utils
from transer import db
from transer import exceptions
from transer.db import btc, sqla_session

from transer.btc.validate_addresses import validate_addrs
from transer.btc.create_transaction import create_raw_transaction
from transer.btc.sign_transaction import sign_raw_transaction


class TestCaseMixin:
    engine = None

    masterkey = 'xprv9s21ZrQH143K4GUqnasvihJkbTvsqE9qWpnumrK8LkFZgpAyk8e' \
                'UALzZaybbPAPwGJKeZtH4oxLgFvcxASq65dYD9P5HeyxJjEgJh22QnMf'

    @classmethod
    def init_db(cls):
        cls.engine = utils.init_db('postgresql://ogaidukov@127.0.0.1:5432/btc_test')

        connection = cls.engine.connect()
        connection.execute('DROP SCHEMA IF EXISTS BTC_PRIVATE, BTC_PUBLIC CASCADE;')
        connection.execute('CREATE SCHEMA IF NOT EXISTS BTC_PRIVATE;')
        connection.execute('CREATE SCHEMA IF NOT EXISTS BTC_PUBLIC;')
        connection.close()

        db.meta.create_all()

    @classmethod
    def init_with_data(cls):
        masterkey = db.btc.MasterKey(
            masterkey_name='electrum',
            priv_masterkey=cls.masterkey,
            treat_as_testnet=True
        )

        bi = db.btc.BitcoindInstance(
            instance_name='Test',
            hostname='127.0.0.1',
            port=18332,
            rpc_user='dummy',
            rpc_passwd='dummy',
            is_https=False
        )

        sqla_session.add_all([masterkey, bi])
        sqla_session.commit()

    @classmethod
    def cleanup_db(cls):
        connection = cls.engine.connect()
        connection.execute('DROP SCHEMA IF EXISTS BTC_PRIVATE, BTC_PUBLIC CASCADE;')
        connection.close()


class BitcoindConnectionTest(unittest.TestCase, TestCaseMixin):
    @classmethod
    def setUpClass(cls):
        cls.init_db()
        cls.init_with_data()

    def test_001_connect(self):
        bi = db.btc.BitcoindInstance.query.filter_by(instance_name='Test').one()
        info = bi.get_rpc_conn().getblockchaininfo()
        self.assertEqual(info['chain'], 'test')

    def test_005_create_addresses_1(self):
        masterkey = db.btc.MasterKey.query.filter_by(masterkey_name='electrum').one()
        bi = db.btc.BitcoindInstance.query.filter_by(instance_name='Test').one()
        res = db.btc.Address.create_addresses(
            bitcoind_inst=bi,
            masterkey=masterkey,
            crypto_path="0",
            from_crypto_num=0,
            num_addrs=10,
            check_integrity=True,
            override_timestamp=datetime(2017, 10, 1)
        )
        self.assertEqual(len(res), 10)

    def test_010_create_addresses_2(self):
        masterkey = db.btc.MasterKey.query.filter_by(masterkey_name='electrum').one()
        bi = db.btc.BitcoindInstance.query.filter_by(instance_name='Test').one()
        res = db.btc.Address.create_addresses(
            bitcoind_inst=bi,
            masterkey=masterkey,
            crypto_path="1",
            from_crypto_num=100,
            num_addrs=3,
            check_integrity=True
        )
        self.assertEqual(len(res), 3)
        self.assertEqual(res[0].crypto_number, 100)


class TransactionValidateTest(unittest.TestCase, TestCaseMixin):
    @classmethod
    def setUpClass(cls):
        cls.init_db()
        cls.init_with_data()

        masterkey = db.btc.MasterKey.query.filter_by(masterkey_name='electrum').one()
        bi = db.btc.BitcoindInstance.query.filter_by(instance_name='Test').one()
        db.btc.Address.create_addresses(
            bitcoind_inst=bi,
            masterkey=masterkey,
            crypto_path="0",
            from_crypto_num=0,
            num_addrs=10,
            check_integrity=True,
            override_timestamp=datetime(2017, 10, 1)
        )

    def test_001_validate_spendables_1(self):
        addresses = ['mtqw5xbgwQXvRB5yhLCvRnUnMBDprVuheY', 'msvaDqBXUfR89QYRq7yZBJE7PtTrNiSTMb']

        bi = db.btc.BitcoindInstance.query.filter_by(instance_name='Test').one()

        _, _, status = validate_addrs(
            bitcoind_inst=bi,
            addresses=addresses,
            estimate_spendables=decimal.Decimal('0.25140000')
        )
        self.assertFalse(status)

    def test_005_validate_spendables_2(self):
        addresses = ['mtqw5xbgwQXvRB5yhLCvRnUnMBDprVuheY', 'msvaDqBXUfR89QYRq7yZBJE7PtTrNiSTMb']

        bi = db.btc.BitcoindInstance.query.filter_by(instance_name='Test').one()

        _, _, status = validate_addrs(
            bitcoind_inst=bi,
            addresses=addresses,
            estimate_spendables=decimal.Decimal('0.25130000')
        )
        self.assertTrue(status)

    def test_0010_validate_spendables_3(self):
        addresses = ['mtqw5xbgwQXvRB5yhLCvRnUnMBDprVuheY', 'msvaDqBXUfR89QYRq7yZBJE7PtTrNiSTMb']

        bi = db.btc.BitcoindInstance.query.filter_by(instance_name='Test').one()

        _, _, status = validate_addrs(
            bitcoind_inst=bi,
            addresses=addresses,
            estimate_spendables=decimal.Decimal('0.25120000'))
        self.assertTrue(status)

    def test_0015_validate_addresses_1(self):
        addresses = ['mtqw5xbgwQXvRB5yhLCvRnUnMBDprVuheY', 'msvaDqBXUfR89QYRq7yZBJE7PtTrNiSTMb']

        bi = db.btc.BitcoindInstance.query.filter_by(instance_name='Test').one()

        addrs, _, _ = validate_addrs(bi, addresses)
        self.assertEqual(len(addrs), 2)

    def test_0020_validate_addresses_2(self):
        addresses = ['mtqw5xbgwQXvRB5yhLCvRnUnMBDprVuheY', 'msvaDqBXUfR89QYRq7yZBJE7PtTrNiSTMb']

        bi = db.btc.BitcoindInstance.query.filter_by(instance_name='Test').one()

        addrs, _, _ = validate_addrs(
            bitcoind_inst=bi,
            addresses=addresses
        )
        addr_vals = list(addrs.values())

        self.assertIsInstance(addr_vals[0]['address_inst'], btc.Address)
        self.assertIsInstance(addr_vals[1]['address_inst'], btc.Address)

    def test_0025_validate_total(self):
        addresses = ['mtqw5xbgwQXvRB5yhLCvRnUnMBDprVuheY', 'msvaDqBXUfR89QYRq7yZBJE7PtTrNiSTMb']

        bi = db.btc.BitcoindInstance.query.filter_by(instance_name='Test').one()

        _, total, _ = validate_addrs(
            bitcoind_inst=bi,
            addresses=addresses
        )
        self.assertEqual(total, decimal.Decimal('0.25130000'))


class TransactionCreateTest(unittest.TestCase, TestCaseMixin):
    @classmethod
    def setUpClass(cls):
        cls.init_db()
        cls.init_with_data()

        masterkey = db.btc.MasterKey.query.filter_by(masterkey_name='electrum').one()
        bi = db.btc.BitcoindInstance.query.filter_by(instance_name='Test').one()
        db.btc.Address.create_addresses(
            bitcoind_inst=bi,
            masterkey=masterkey,
            crypto_path="0",
            from_crypto_num=0,
            num_addrs=20,
            check_integrity=True,
            override_timestamp=datetime(2017, 10, 1)
        )

    def test_001_create_raw_transaction_1(self):
        addresses = ['mtqw5xbgwQXvRB5yhLCvRnUnMBDprVuheY', 'msvaDqBXUfR89QYRq7yZBJE7PtTrNiSTMb']

        bi = db.btc.BitcoindInstance.query.filter_by(instance_name='Test').one()

        _, trx = create_raw_transaction(
            bitcoind_inst=bi,
            sources=addresses,
            destination='n4iPaun9gjH5kEwWr92eph3QDXPsUmDUHr',
            amount=decimal.Decimal('0.25130000'),
            change='mqU8DCkXC2w5BjQejeKoeY9jM2a4V3uEub',
            fee=decimal.Decimal(0)
        )

        # amount равен сумме utxo-s -- один vout
        self.assertEqual(len(trx['vout']), 1)

    def test_005_create_raw_transaction_2(self):
        addresses = ['mtqw5xbgwQXvRB5yhLCvRnUnMBDprVuheY', 'msvaDqBXUfR89QYRq7yZBJE7PtTrNiSTMb']

        bi = db.btc.BitcoindInstance.query.filter_by(instance_name='Test').one()

        _, trx = create_raw_transaction(
            bitcoind_inst=bi,
            sources=addresses,
            destination='n4iPaun9gjH5kEwWr92eph3QDXPsUmDUHr',
            amount=decimal.Decimal('0.25120000'),
            change='mqU8DCkXC2w5BjQejeKoeY9jM2a4V3uEub',
            fee=decimal.Decimal(0)
        )

        # amount меньше суммы utxo-s -- два vout-s: на destination и на change
        self.assertEqual(len(trx['vout']), 2)

    def test_010_create_raw_transaction_3(self):
        addresses = ['mtqw5xbgwQXvRB5yhLCvRnUnMBDprVuheY', 'msvaDqBXUfR89QYRq7yZBJE7PtTrNiSTMb']

        bi = db.btc.BitcoindInstance.query.filter_by(instance_name='Test').one()

        # amount больше суммы utxo-s -- raise BtcCreateTransactionException()
        with self.assertRaises(exceptions.BtcCreateTransactionException):
            _, _ = create_raw_transaction(
                bitcoind_inst=bi,
                sources=addresses,
                destination='n4iPaun9gjH5kEwWr92eph3QDXPsUmDUHr',
                amount=decimal.Decimal('0.25140000'),
                change='mqU8DCkXC2w5BjQejeKoeY9jM2a4V3uEub',
                fee=decimal.Decimal(0)
            )


class TransactionSignTest(unittest.TestCase, TestCaseMixin):
    @classmethod
    def setUpClass(cls):
        cls.init_db()
        cls.init_with_data()

        masterkey = db.btc.MasterKey.query.filter_by(masterkey_name='electrum').one()
        bi = db.btc.BitcoindInstance.query.filter_by(instance_name='Test').one()
        db.btc.Address.create_addresses(
            bitcoind_inst=bi,
            masterkey=masterkey,
            crypto_path="0",
            from_crypto_num=0,
            num_addrs=20,
            check_integrity=True,
            override_timestamp=datetime(2017, 10, 1)
        )

    def test_001_sign_raw_transaction_1(self):
        addresses = ['mtqw5xbgwQXvRB5yhLCvRnUnMBDprVuheY', 'msvaDqBXUfR89QYRq7yZBJE7PtTrNiSTMb']

        bi = db.btc.BitcoindInstance.query.filter_by(instance_name='Test').one()

        trx_h, trx = create_raw_transaction(
            bitcoind_inst=bi,
            sources=addresses,
            destination='n4iPaun9gjH5kEwWr92eph3QDXPsUmDUHr',
            amount=decimal.Decimal('0.25130000'),
            change='mqU8DCkXC2w5BjQejeKoeY9jM2a4V3uEub',
            fee=decimal.Decimal(0)
        )

        _, signed_trx = sign_raw_transaction(
            bitcoind_inst=bi,
            signing_addrs=addresses,
            trx_h=trx_h
        )

        # amount равен сумме utxo-s -- один vout
        self.assertEqual(len(signed_trx['vout']), 1)

    def test_005_sign_raw_transaction_2(self):
        addresses = ['mtqw5xbgwQXvRB5yhLCvRnUnMBDprVuheY', 'msvaDqBXUfR89QYRq7yZBJE7PtTrNiSTMb']

        bi = db.btc.BitcoindInstance.query.filter_by(instance_name='Test').one()

        trx_h, trx = create_raw_transaction(
            bitcoind_inst=bi,
            sources=addresses,
            destination='n4iPaun9gjH5kEwWr92eph3QDXPsUmDUHr',
            amount=decimal.Decimal('0.25130000'),
            change='mqU8DCkXC2w5BjQejeKoeY9jM2a4V3uEub',
            fee=decimal.Decimal(0)
        )

        # не все UTXOs будут подписаны
        addresses.pop()

        with self.assertRaises(exceptions.BtcSignTransactionException):
            _, signed_trx = sign_raw_transaction(
                bitcoind_inst=bi,
                signing_addrs=addresses,
                trx_h=trx_h
            )
