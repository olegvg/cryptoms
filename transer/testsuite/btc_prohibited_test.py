from datetime import datetime
import decimal
import unittest

from transer import db

from transer.btc.create_transaction import create_raw_transaction
from transer.btc.sign_transaction import sign_raw_transaction
from transer.btc.send_transaction import send_raw_transaction
from .btc_test import TestCaseMixin


class TransactionSendTest(unittest.TestCase, TestCaseMixin):
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

    def test_001_send_funds_1(self):
        addresses = ['muXB2duZRxARUjK4vTdmQEUm9P5kGXwYjn', 'mohtHWsyJEigxbZu2ER8ctgfQ1dCNWxzBx']

        bi = db.btc.BitcoindInstance.query.filter_by(instance_name='Test').one()

        trx_h, _ = create_raw_transaction(
            bitcoind_inst=bi,
            sources=addresses,
            destination='mqU8DCkXC2w5BjQejeKoeY9jM2a4V3uEub',
            amount=decimal.Decimal('2.0'),
            change='mxTAwhBSZzKV49jAhKVjxV1YiVEJnaJbYi',
            fee=decimal.Decimal('0.00001'),
            confirmations=1
        )

        signed_trx_h, signed_trx = sign_raw_transaction(
            bitcoind_inst=bi,
            signing_addrs=addresses,
            trx_h=trx_h
        )

        sent_trx = send_raw_transaction(
            bitcoind_inst=bi,
            signed_trx_h=signed_trx_h
        )

        self.assertIsInstance(sent_trx, str)

    def test_005_send_funds_2(self):
        addresses = ['mqU8DCkXC2w5BjQejeKoeY9jM2a4V3uEub']

        bi = db.btc.BitcoindInstance.query.filter_by(instance_name='Test').one()

        trx_h, _ = create_raw_transaction(
            bitcoind_inst=bi,
            sources=addresses,
            destination='muXB2duZRxARUjK4vTdmQEUm9P5kGXwYjn',
            amount=decimal.Decimal('1.0'),
            change='mohtHWsyJEigxbZu2ER8ctgfQ1dCNWxzBx',
            fee=decimal.Decimal('0.00001'),
            confirmations=1
        )

        signed_trx_h, signed_trx = sign_raw_transaction(
            bitcoind_inst=bi,
            signing_addrs=addresses,
            trx_h=trx_h
        )

        from pprint import pprint
        pprint(signed_trx)

        sent_trx = send_raw_transaction(
            bitcoind_inst=bi,
            signed_trx_h=signed_trx_h
        )

        self.assertIsInstance(sent_trx, str)
