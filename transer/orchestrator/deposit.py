import uuid
import urllib3
import json

from transer import types, config, schemata
from transer.btc import monitor_transaction
from transer.db import sqla_session
from transer.db import btc, transaction
from transer.exceptions import BtcMonitorTransactionException


def periodic_check_deposit_btc():
    btcd_instance_name = config['btcd_instance_name']

    recorded_transactions_q = transaction.CryptoDepositTransaction.query.filter(
        transaction.CryptoDepositTransaction.status == types.DepositStatus.PENDING.value
    )
    recorded_transactions = recorded_transactions_q.all()
    for t in recorded_transactions:
        txid = t.txid
        address = t.address
        u_txid_seed = f'{address}.{txid}'
        u_txid = uuid.uuid5(uuid.NAMESPACE_URL, u_txid_seed)

        try:
            tx_info = monitor_transaction.get_txid_status(
                bt_name=btcd_instance_name,
                txid=txid
            )
        except BtcMonitorTransactionException:
            t.status = types.DepositStatus.CANCELLED.value    # in case of chain rebuilt
            t.is_acknowledged = False
            print("2", u_txid, t.address, t.amount, t.status)
            # loop.request ....
            continue

        confirmations = tx_info['confirmations']
        if confirmations >= 6:
            t.status = types.DepositStatus.COMPLETED.value
            t.is_acknowledged = False
            print("3", u_txid, address, t.amount, t.status)
            # loop.request ....

    sqla_session.commit()

    txs = monitor_transaction.get_recent_deposit_transactions(
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
        status = types.DepositStatus.PENDING.value if confirmations < 6 else types.DepositStatus.COMPLETED.value
        deposit_transaction = transaction.CryptoDepositTransaction(
            u_txid=u_txid,
            currency=types.CryptoCurrency.BITCOIN.value,
            address=address,
            amount=amount,
            txid=txid,
            status=status,
            is_acknowledged=False
        )
        sqla_session.add(deposit_transaction)
        print("1", u_txid, address, amount, status)
        # loop.request ....
    sqla_session.commit()


def periodic_send_deposit_btc():
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
            'amount': t.amount,
            'currency': types.CryptoCurrency.BITCOIN.value,
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
