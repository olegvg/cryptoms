import unittest

from transer import exceptions

from transer.eth import validate_address, manipulate_addresses, \
    create_transaction, sign_transaction, send_transaction


class TestCaseMixin:
    eth_url = 'http://127.0.0.1:48545'
    rinkeby_wallet_1 = '98e9569ea34764a7cb9dd4ad167287791153149f1c7be93cec9f67ba4663f76e'  # private key
    rinkeby_address_1 = '6412FCedCedEb20a8bB990C6041D2CDEE0404Fa7'  # address

    rinkeby_wallet_2 = 'ab0ba203eba807b668025bfc42764bb23ddd522912ec06a77e506872e41cb0e0'  # private key
    rinkeby_address_2 = '28c8c4eac85b180b2753319466327156a3d2ff98'  # address


class EthAddressValidationTest(unittest.TestCase, TestCaseMixin):
    def test_001_normalize_addr_1(self):
        norm_address = '0x' + self.rinkeby_address_1.lower()

        self.assertEqual(norm_address, validate_address.normalize_addr(self.rinkeby_address_1))

    def test_005_normalize_addr_2(self):
        invalid_addr = '0X' + self.rinkeby_address_1.lower()

        with self.assertRaises(exceptions.EthAddressIntegrityException):
            validate_address.normalize_addr(invalid_addr)

    def test_010_validate_addr_1(self):
        res = validate_address.validate_existence_addr(self.eth_url, self.rinkeby_address_1)
        self.assertIsNone(res)

    def test_015_validate_addr_2(self):
        res = validate_address.validate_existence_addr(self.eth_url, self.rinkeby_address_1, '10.0')
        self.assertTrue(res)


class EthAddressManipulationTest(unittest.TestCase, TestCaseMixin):
    def test_001_create_privkeys_01(self):
        priv_keys = manipulate_addresses.create_priv_keys(num_keys=30)
        self.assertEqual(len(priv_keys), 30)
        for p in priv_keys:
            self.assertEqual(len(p), 64)

    def test_005_create_keypairs_01(self):
        keypairs = manipulate_addresses.create_keypairs(num_keypairs=30)
        self.assertEqual(len(keypairs), 30)
        for a, p in keypairs.items():
            self.assertEqual(len(a), 40)
            self.assertEqual(len(p), 64)


class EthTransactionCreateTest(unittest.TestCase, TestCaseMixin):
    def test_001_check_gas_price_01(self):
        gas_price = create_transaction.current_gas_price(self.eth_url)
        self.assertLess(gas_price, 1e-6)    # will be enough forever :-)

    def test_005_check_gas_price_02(self):
        gas_price = create_transaction.current_gas_price(self.eth_url)
        self.assertGreater(gas_price, 1e-12)

    def test_010_create_transaction_01(self):
        gas_price = create_transaction.current_gas_price(self.eth_url)

        tx_h = create_transaction.create_transaction(
            web3_url=self.eth_url,
            src_addr=self.rinkeby_address_1,
            dst_addr=self.rinkeby_address_2,
            amount='0.1',
            gas_price=gas_price
        )
        self.assertEqual(len(tx_h), 90)


class EthTransactionSignTest(unittest.TestCase, TestCaseMixin):
    def test_001_sign_01(self):
        gas_price = create_transaction.current_gas_price(self.eth_url)

        unsigned_tx_h = create_transaction.create_transaction(
            web3_url=self.eth_url,
            src_addr=self.rinkeby_address_1,
            dst_addr=self.rinkeby_address_2,
            amount='0.1',
            gas_price=gas_price
        )
        self.assertEqual(len(unsigned_tx_h), 90)

        signed_tx = sign_transaction.sign_transaction(
            src_addr=self.rinkeby_address_1,
            priv_key=self.rinkeby_wallet_1,
            unsigned_tx_h=unsigned_tx_h,
            network_id=4    # Rinkeby network
        )
        self.assertEqual(len(signed_tx), 90)


class EthTransactionSendTest(unittest.TestCase, TestCaseMixin):
    def test_001_send_01(self):
        gas_price = create_transaction.current_gas_price(self.eth_url)

        unsigned_tx_h = create_transaction.create_transaction(
            web3_url=self.eth_url,
            src_addr=self.rinkeby_address_1,
            dst_addr=self.rinkeby_address_2,
            amount='0.1',
            gas_price=gas_price
        )
        self.assertEqual(len(unsigned_tx_h), 90)

        signed_tx = sign_transaction.sign_transaction(
            src_addr=self.rinkeby_address_1,
            priv_key=self.rinkeby_wallet_1,
            unsigned_tx_h=unsigned_tx_h,
            network_id=4    # Rinkeby network
        )
        self.assertEqual(len(signed_tx), 222)

        tx_id = send_transaction.send_transaction(
            web3_url=self.eth_url,
            signed_tx_h=signed_tx
        )
        self.assertEqual(len(tx_id), 66)

    def test_005_mined_enough_01(self):
        res = send_transaction.check_transaction_mined(
            web3_url=self.eth_url,
            tx_hash='0xdd10f69d8ab6d0b3b35e8de390e48459942858c97e3dfb4f6ec24fbdfec20613',
            blocks_depth=15
        )
        self.assertTrue(res)

    def test_010_mined_enough_02(self):
        res = send_transaction.check_transaction_mined(
            web3_url=self.eth_url,
            tx_hash='0xdd10f69d8ab6d0b3b35e8de390e48459942858c97e3dfb4f6ec24fbdfec20613',
            blocks_depth=1500000000     # somewhen... :-)
        )
        self.assertFalse(res)

    def test_015_mined_enough_03(self):
        res = send_transaction.check_transaction_mined(
            web3_url=self.eth_url,
            tx_hash='0xdd10f69d8ab6d0b3b35e8de390e48459942858c97e3dfb4f6ec24fbdfec20614',  # fake tx id
            blocks_depth=1
        )
        self.assertIsNone(res)
