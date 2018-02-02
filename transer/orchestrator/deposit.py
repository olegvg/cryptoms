import uuid
import urllib3
import json

from transer import types, config, schemata
from transer.btc import monitor_transaction as btc_mon
from transer.eth import monitor_transaction as eth_mon
from transer.db import sqla_session, btc, eth, transaction
from transer.exceptions import BtcMonitorTransactionException, EthMonitorTransactionException


def add_confirmed_deposit_btc(address, amount):
    address_to_update_q = btc.Address.query.filter(
        btc.Address.address == address
    )
    address_to_update = address_to_update_q.one()
    address_to_update.amount += amount


def periodic_check_deposit_btc():
    btcd_instance_name = config['btcd_instance_name']

    recorded_transactions_q = transaction.CryptoDepositTransaction.query.filter(
        transaction.CryptoDepositTransaction.status == types.DepositStatus.PENDING.value,
        transaction.CryptoDepositTransaction.currency == types.CryptoCurrency.BITCOIN.value
    )
    recorded_transactions = recorded_transactions_q.all()
    for t in recorded_transactions:
        txid = t.txid

        try:
            tx_info = btc_mon.get_txid_status(
                bt_name=btcd_instance_name,
                txid=txid
            )
        except BtcMonitorTransactionException:
            t.status = types.DepositStatus.CANCELLED.value    # in case of chain rebuilt
            t.is_acknowledged = False
            continue

        confirmations = tx_info['confirmations']
        if confirmations >= 6:
            add_confirmed_deposit_btc(t.address, t.amount)
            t.status = types.DepositStatus.COMPLETED.value
            t.is_acknowledged = False

    sqla_session.commit()

    txs = btc_mon.get_recent_deposit_transactions(
        bt_name=btcd_instance_name,
        confirmations=1
    )
    # Controversial approach here: some data might be lost
    # between get_recent_deposit_transactions() and upcoming sqla_session.commit().
    # It may be relied only on subsequent Postgres/Redshift layer reliability
    for t in txs:
        address = t['address']
        amount = t['amount']
        txid = t['txid']
        confirmations = t['confirmations']
        u_txid_seed = f'{address}.{txid}'
        u_txid = uuid.uuid5(uuid.NAMESPACE_URL, u_txid_seed)
        status = types.DepositStatus.PENDING if confirmations < 6 else types.DepositStatus.COMPLETED
        deposit_transaction = transaction.CryptoDepositTransaction(
            u_txid=u_txid,
            currency=types.CryptoCurrency.BITCOIN.value,
            address=address,
            amount=amount,
            txid=txid,
            status=status.value,
            is_acknowledged=False
        )
        sqla_session.add(deposit_transaction)

        if status == types.DepositStatus.COMPLETED:
            add_confirmed_deposit_btc(address, amount)

    sqla_session.commit()


def periodic_send_deposit():
    deposit_notification_endpoint = config['deposit_notification_endpoint']

    unacknowledged_transactions_q = transaction.CryptoDepositTransaction.query.filter(
        transaction.CryptoDepositTransaction.is_acknowledged.is_(False)
    )
    unacknowledged_transactions = unacknowledged_transactions_q.all()

    http = urllib3.PoolManager()
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
                deposit_notification_endpoint,
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


def add_confirmed_deposit_eth(address, amount):
    address_to_update_q = eth.Address.query.filter(
        eth.Address.address == address
    )
    address_to_update = address_to_update_q.one()
    address_to_update.amount += amount


def periodic_check_deposit_eth():
    etcd_instance_uri = config['etcd_instance_uri']

    recorded_transactions_q = transaction.CryptoDepositTransaction.query.filter(
        transaction.CryptoDepositTransaction.status == types.DepositStatus.PENDING.value,
        transaction.CryptoDepositTransaction.currency == types.CryptoCurrency.ETHERIUM.value
    )
    recorded_transactions = recorded_transactions_q.all()
    for t in recorded_transactions:
        tx_hash = t.txid

        try:
            tx_info = eth_mon.get_transaction(
                web3_url=etcd_instance_uri,
                tx_hash=tx_hash
            )
        except EthMonitorTransactionException:
            t.status = types.DepositStatus.CANCELLED.value    # in case of chain rebuilt
            t.is_acknowledged = False
            continue

        confirmations = tx_info['confirmations']
        if confirmations >= 12:
            add_confirmed_deposit_eth(t.address, t.amount)
            t.status = types.DepositStatus.COMPLETED.value
            t.is_acknowledged = False

    sqla_session.commit()

    deposits = eth_mon.get_recent_deposit_transactions(etcd_instance_uri)

    for address in deposits:
        for tx in deposits[address]:
            txid = tx['tx_hash']
            amount = tx['amount']
            u_txid_seed = f'{address}.{txid}'
            u_txid = uuid.uuid5(uuid.NAMESPACE_URL, u_txid_seed)
            status = types.DepositStatus.PENDING if tx['confirmations'] < 12 else types.DepositStatus.COMPLETED
            deposit_transaction = transaction.CryptoDepositTransaction(
                u_txid=u_txid,
                currency=types.CryptoCurrency.ETHERIUM.value,
                address=address,
                amount=amount,
                txid=txid,
                status=status.value,
                is_acknowledged=False
            )
            sqla_session.add(deposit_transaction)

            if status == types.DepositStatus.COMPLETED:
                add_confirmed_deposit_eth(address, amount)

    sqla_session.commit()
