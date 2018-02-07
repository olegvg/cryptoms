import decimal
import json

import certifi
import urllib3

from sqlalchemy import desc, asc
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from transer import config, types, schemata
from transer.exceptions import TransactionInconsistencyError, EthMonitorTransactionException
from transer.db import eth, btc, transaction, sqla_session
from transer.types import CryptoCurrency, WithdrawalStatus

from transer.btc.create_transaction import calculate_transaction_fee as btc_calculate_transaction_fee
from transer.btc.create_transaction import create_transaction as btc_create_transaction
from transer.btc.sign_transaction import sign_transaction as btc_sign_transaction
from transer.btc.send_transaction import send_transaction as btc_send_transaction
from transer.btc.monitor_transaction import get_txid_status as btc_get_txid_status

from transer.eth.create_transaction import current_gas_price as eth_current_gas_price
from transer.eth.create_transaction import create_transaction as eth_create_transaction
from transer.eth.sign_transaction import sign_transaction as eth_sign_transaction
from transer.eth.send_transaction import send_transaction as eth_send_transaction
from transer.eth.monitor_transaction import get_transaction as eth_get_transaction
from transer.eth.create_transaction import TRANSACTION_GAS
from transer.eth import eth_divider


def withdraw_btc(u_txid, address, amount):
    """

    :param u_txid: UUID4 идентификатор транзакции в сервисе cryptopay
    :param address: адрес, на который нужно сделать перечилсение;
        запрещены перечисления членам системы / на адреса, принадлежащие системе используя внешнюю Bitcoin сеть
    :param amount: объём битокойнов
    :return:
    """
    # explicitly prohibit withdrawals to addresses belong to Cryptology
    # i.e. cryptopayments between clients via external Bitcoin network
    check_addr = btc.Address.query.filter(
        btc.Address.address == address
    ).count()
    if check_addr > 0:  # == 1 actually
        return WithdrawalStatus.FAILED.value

    u_txid_q = transaction.CryptoWithdrawTransaction.query.filter(
        transaction.CryptoWithdrawTransaction.u_txid == u_txid
    )

    try:
        crypto_transaction = u_txid_q.one()
        return crypto_transaction.status
    except MultipleResultsFound as e:
        sqla_session.rollback()
        raise TransactionInconsistencyError(f'Multiple transaction records found for {u_txid}. Report the bug') from e
    except NoResultFound:
        crypto_transaction = transaction.CryptoWithdrawTransaction(
            u_txid=u_txid,
            currency=CryptoCurrency.BITCOIN.value,
            address=address,
            amount=amount,
            status=WithdrawalStatus.FAILED.value
        )
        sqla_session.add(crypto_transaction)

        btcd_instance_name = config['btcd_instance_name']
        key_name = config['btc_masterkey_name']
        masterkey_q = btc.MasterKey.query.filter(
            btc.MasterKey.masterkey_name == key_name
        )
        masterkey = masterkey_q.one()

        bitcoind_instance_q = btc.BitcoindInstance.query.filter(
            btc.BitcoindInstance.instance_name == btcd_instance_name
        )
        bitcoind_inst = bitcoind_instance_q.one()

        # given that num of UTXOs ~ num of Addresses and fee is ~$2 per UTXO
        # so let it be no more 10 UTXOs/Addresses to feed the destination at cost ~$20 and one wallet for change
        ordered_adresses_q = btc.Address.query.filter(
            btc.Address.bitcoind_inst == bitcoind_inst,
            btc.Address.masterkey == masterkey,
            btc.Address.address != address
        ).order_by(desc(btc.Address.amount)).limit(11)
        candidates = ordered_adresses_q.all()

        change_address = candidates.pop(-1)

        estimate_amount = decimal.Decimal(0.0)

        projected_fee = btc_calculate_transaction_fee(
            bt_name=btcd_instance_name,
            sources=[c.address for c in candidates], destination=address,
            change=change_address.address,
            preferred_blocks=5  # Anton don't like such numbers :-)
        )

        src_address_objs = []
        for c in candidates:
            estimate_amount += c.amount
            src_address_objs.append(c)
            if estimate_amount > amount + projected_fee:
                break
        if estimate_amount < amount + projected_fee:
            # Insufficient funds
            sqla_session.commit()
            return crypto_transaction.status

        src_addresses = [x.address for x in src_address_objs]

        # Equation 'projected_fee >= actual_fee' is always true
        actual_fee = btc_calculate_transaction_fee(
            bt_name=btcd_instance_name,
            sources=[src_addresses],
            destination=address,
            change=change_address.address,
            preferred_blocks=5  # Anton don't like such numbers :-)
        )

        trx, _ = btc_create_transaction(
            bt_name=bitcoind_inst.instance_name,
            sources=src_addresses,
            destination=address,
            amount=amount,
            change=change_address.address,
            fee=actual_fee
        )

        signed_trx, _ = btc_sign_transaction(
            bt_name=bitcoind_inst.instance_name,
            signing_addrs=src_addresses,
            trx=trx
        )

        # It would be a race condition between section starting from send_transaction() to sqla_session.commit()
        # and monitor_transaction.get_recent_deposit_transactions(), if get_recent_deposit_transactions() taken
        # into account transactions with num of confirmations equals to 0 (mempool/unconfirmed transactions).
        # Doesn't actual condition now
        txid = btc_send_transaction(
            bt_name=bitcoind_inst.instance_name,
            signed_trx=signed_trx
        )

        crypto_transaction.status = WithdrawalStatus.PENDING.value
        crypto_transaction.txids = [txid]

        change_address_log = btc.ChangeTransactionLog(
            change_address=change_address.address,
            change_tx_id=txid
        )
        sqla_session.add(change_address_log)

        # all the funds move to change address
        for a in src_address_objs:
            a.amount = decimal.Decimal(0.0)

        sqla_session.commit()
        return crypto_transaction.status


def withdrawal_status_btc(crypto_transaction):
    btcd_instance_name = config['btcd_instance_name']

    try:
        txid = crypto_transaction.txids[0]  # in btc, only one txid per transaction
    except (KeyError, TypeError):
        return WithdrawalStatus.FAILED.value

    tx_info = btc_get_txid_status(
        bt_name=btcd_instance_name,
        txid=txid
    )

    if crypto_transaction.status == WithdrawalStatus.COMPLETED.value:
        return

    try:
        confirmations = tx_info['confirmations']
    except KeyError as e:
        if txid == tx_info['txid']:
            crypto_transaction.status = WithdrawalStatus.PENDING.value
            crypto_transaction.is_acknowledged = False
            return
        else:
            sqla_session.rollback()
            raise TransactionInconsistencyError(f'Programming error with {txid}. Call the programmer') from e

    if confirmations >= 6 and crypto_transaction.status != WithdrawalStatus.COMPLETED.value:
        crypto_transaction.status = WithdrawalStatus.COMPLETED.value
        crypto_transaction.is_acknowledged = False

        change_tx_q = btc.ChangeTransactionLog.query.filter(
            btc.ChangeTransactionLog.change_tx_id == txid
        )
        change_tx = change_tx_q.one()

        txs = tx_info['vout']
        addrs = {t['scriptPubKey']['addresses'][0]: t['value'] for t in txs}

        address_q = btc.Address.query.filter(
            btc.Address.address == change_tx.change_address,
            btc.Address.is_populated.is_(True)
        )
        address = address_q.one()
        address.amount += addrs[change_tx.change_address]

    elif confirmations > 0:
        crypto_transaction.status = WithdrawalStatus.PENDING.value
        crypto_transaction.is_acknowledged = False


def periodic_check_withdraw_btc():
    crypto_transaction_q = transaction.CryptoWithdrawTransaction.query.filter(
        transaction.CryptoWithdrawTransaction.status == types.WithdrawalStatus.PENDING.value,
        transaction.CryptoWithdrawTransaction.currency == types.CryptoCurrency.BITCOIN.value
    )

    crypto_transactions = crypto_transaction_q.all()

    for cw_trx in crypto_transactions:
        withdrawal_status_btc(cw_trx)

    sqla_session.commit()


def periodic_check_withdraw_eth():
    crypto_transaction_q = transaction.CryptoWithdrawTransaction.query.filter(
        transaction.CryptoWithdrawTransaction.status == types.WithdrawalStatus.PENDING.value,
        transaction.CryptoWithdrawTransaction.currency == types.CryptoCurrency.ETHERIUM.value
    )

    crypto_transactions = crypto_transaction_q.all()

    for cw_trx in crypto_transactions:
        withdrawal_status_eth(cw_trx)

    sqla_session.commit()


def periodic_send_withdraw():
    withdraw_notification_endpoint = config['withdraw_notification_endpoint']

    unacknowledged_transactions_q = transaction.CryptoWithdrawTransaction.query.filter(
        transaction.CryptoWithdrawTransaction.is_acknowledged.is_(False)
    )
    unacknowledged_transactions = unacknowledged_transactions_q.all()

    http = urllib3.PoolManager(
        ca_certs=certifi.where(),
        cert_reqs='CERT_REQUIRED'
    )
    for t in unacknowledged_transactions:

        data = {
            'tx_id': str(t.u_txid),
            'wallet_addr': t.address,
            'amount': str(t.amount),
            'currency': t.currency,
            'status': t.status
        }

        withdraw_req = schemata.DepositRequest(data)
        withdraw_req.validate()

        encoded_data = json.dumps(data).encode('utf-8')
        try:
            resp = http.request(
                'POST',
                withdraw_notification_endpoint,
                body=encoded_data,
                headers={'Content-Type': 'application/json'},
                retries=10
            )
        except urllib3.exceptions.HTTPError:
            pass
        else:
            if resp.status in [200, 201]:
                t.is_acknowledged = True

    sqla_session.commit()


def withdraw_eth(u_txid, address, amount):
    """

    :param u_txid: UUID4 идентификатор транзакции в сервисе cryptopay
    :param address: адрес, на который нужно сделать перечилсение
    :param amount: объём битокойнов
    :return:
    """
    u_txid_q = transaction.CryptoWithdrawTransaction.query.filter(
        transaction.CryptoWithdrawTransaction.u_txid == u_txid
    )

    try:
        crypto_transaction = u_txid_q.one()
        return crypto_transaction.status
    except MultipleResultsFound as e:
        sqla_session.rollback()
        raise TransactionInconsistencyError(f'Multiple transaction records found for {u_txid}. Report the bug') from e
    except NoResultFound:
        crypto_transaction = transaction.CryptoWithdrawTransaction(
            u_txid=u_txid,
            currency=CryptoCurrency.ETHERIUM.value,
            address=address,
            amount=amount,
            status=WithdrawalStatus.FAILED.value
        )
        sqla_session.add(crypto_transaction)

        ethd_instance_uri = config['ethd_instance_uri']
        eth_masterkey_name = config['eth_masterkey_name']

        gas_price = eth_current_gas_price(ethd_instance_uri)
        fee = TRANSACTION_GAS * gas_price

        masterkey_q = eth.MasterKey.query.filter(
            eth.MasterKey.masterkey_name == eth_masterkey_name
        )
        masterkey = masterkey_q.one()

        ordered_adresses_q = eth.Address.query.filter(
            eth.Address.masterkey == masterkey,
            eth.Address.address != address,
            eth.Address.amount > fee    # don't dive into gold sand
        ).order_by(asc(eth.Address.amount))
        candidates = ordered_adresses_q.all()

        approx_amount = amount
        spendables = {}
        for c in candidates:
            remain_amount = c.amount - fee
            withdraw_amount = remain_amount if remain_amount < approx_amount else approx_amount

            if withdraw_amount < fee:   # prevent weird spending transactions with amount less than fee
                break

            approx_amount -= withdraw_amount
            spendables[c] = withdraw_amount

            if approx_amount == decimal.Decimal(0.0):
                break
        else:
            # Insufficient funds
            sqla_session.commit()
            return crypto_transaction.status

        tx_ids = []
        for s, a in spendables.items():
            utx_h = eth_create_transaction(
                web3_url=ethd_instance_uri,
                src_addr=s.address,
                dst_addr=address,
                amount=a,
                gas_price=gas_price
            )

            stx_h = eth_sign_transaction(
                src_addr=s.address,
                priv_key=s.get_priv_key(),
                unsigned_tx_h=utx_h,
                network_id=masterkey.network_id
            )

            tx_id = eth_send_transaction(
                web3_url=ethd_instance_uri,
                signed_tx_h=stx_h
            )
            tx_ids.append(tx_id)

        crypto_transaction.txids = tx_ids
        crypto_transaction.status = types.WithdrawalStatus.PENDING.value

        sqla_session.commit()
        return crypto_transaction.status


def withdrawal_status_eth(crypto_transaction):
    ethd_instance_uri = config['ethd_instance_uri']
    pending_txids = crypto_transaction.txids[:]
    completed_txids = crypto_transaction.completed_txids[:]

    complete_c = len(pending_txids)
    for txid in pending_txids[:]:
        try:
            tx = eth_get_transaction(web3_url=ethd_instance_uri, tx_hash=txid)
        except EthMonitorTransactionException:
            # one of transactions was unsuccessful / disappeared so there is partial withdrawing
            # and payment transaction will remain PENDING until manual investigation
            pass
        if tx['confirmations'] >= 12:
            address = eth.Address.query.filter(
                eth.Address.address == tx['from'].lower()
            ).one()
            address.amount -= tx['value'] / eth_divider

            complete_c -= 1
            completed_txids.append(txid)
            pending_txids.remove(txid)

    # deep update whole sqla.ARRAY as alternative
    # to Mutation Tracking http://docs.sqlalchemy.org/en/latest/orm/extensions/mutable.html
    crypto_transaction.completed_txids = completed_txids
    crypto_transaction.txids = pending_txids

    if complete_c == 0:
        crypto_transaction.status = types.WithdrawalStatus.COMPLETED.value
