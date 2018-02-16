import json
from functools import partial

import certifi
import urllib3
from jsonrpc.utils import DatetimeDecimalEncoder
from aiohttp.web import json_response, Response

from sqlalchemy.orm.exc import NoResultFound

from transer import schemata, config, types
from transer.db import transaction, sqla_session
from transer.types import CryptoCurrency, WithdrawalStatus

from transer.orchestrator import withdraw, claim_wallet_addr, reconciliation


def claim_wallet_addr_endpoint(sync_request):
    currency = sync_request['match_info']['currency']

    # strange redundant validator :-)
    if currency not in [x.value for x in CryptoCurrency]:
        resp = Response()
        resp_text = f'Crypto currency ticker {currency} is not supported'
        resp.set_status(501, resp_text)
        resp.text = resp_text
        return resp

    handlers = {
        CryptoCurrency.BITCOIN.value: claim_wallet_addr.claim_btc_addr,
        CryptoCurrency.ETHERIUM.value: claim_wallet_addr.claim_eth_addr
    }

    handler_func = handlers.get(currency, lambda **_: WithdrawalStatus.FAILED.value)

    status = handler_func()

    return json_response(status)


def reconcile_addresses_endpoint(sync_request, enforce=False):
    currency = sync_request['match_info']['currency']

    # strange redundant validator :-)
    if currency not in [x.value for x in CryptoCurrency]:
        resp = Response()
        resp_text = f'Crypto currency ticker {currency} is not supported'
        resp.set_status(501, resp_text)
        resp.text = resp_text
        return resp

    handlers = {
        CryptoCurrency.BITCOIN.value: reconciliation.reconcile_btc,
    }

    handler_func = handlers.get(currency, lambda **_: WithdrawalStatus.FAILED)
    res = handler_func(enforce=enforce)

    if res == WithdrawalStatus.FAILED:
        resp = Response()
        resp_text = 'Notable failure. Call the programmer'
        resp.set_status(503, resp_text)
        resp.text = resp_text
        return resp

    dumps = partial(json.dumps, cls=DatetimeDecimalEncoder)
    return json_response({'actual_balances': res}, dumps=dumps)


def withdraw_endpoint(sync_request):
    data = sync_request['json']
    withdraw_req = schemata.WithdrawRequest(data)
    withdraw_req.validate()

    handlers = {
        CryptoCurrency.BITCOIN.value: withdraw.withdraw_btc,
        CryptoCurrency.ETHERIUM.value: withdraw.withdraw_eth
    }

    handler_func = handlers.get(data['currency'], lambda **_: WithdrawalStatus.FAILED.value)

    status = handler_func(
        u_txid=withdraw_req.tx_id,
        address=withdraw_req.wallet_addr,
        amount=withdraw_req.amount
    )

    resp_data = {'tx_id': data['tx_id'], 'status': status}
    withdraw_req = schemata.WithdrawResponse(resp_data)
    withdraw_req.validate()
    return json_response(resp_data)


def withdrawal_status_endpoint(sync_request):
    u_txid = sync_request['match_info']['u_txid']

    crypto_transaction_q = transaction.CryptoWithdrawTransaction.query.filter(
        transaction.CryptoWithdrawTransaction.u_txid == u_txid
    )

    try:
        crypto_transaction = crypto_transaction_q.one()
    except NoResultFound:
        resp_data = {'tx_id': u_txid, 'status': types.WithdrawalStatus.FAILED.value}
        withdraw_req = schemata.WithdrawResponse(resp_data)
        withdraw_req.validate()
        return json_response(resp_data)

    handlers = {
        CryptoCurrency.BITCOIN.value: withdraw.withdrawal_status_btc,
        CryptoCurrency.ETHERIUM.value: withdraw.withdrawal_status_eth
    }
    handler_func = handlers.get(crypto_transaction.currency, lambda **_: WithdrawalStatus.FAILED.value)

    handler_func(crypto_transaction)

    sqla_session.commit()

    resp_data = {'tx_id': u_txid, 'status': crypto_transaction.status}
    withdraw_req = schemata.WithdrawResponse(resp_data)
    withdraw_req.validate()
    return json_response(resp_data)


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
            'status': t.status
        }
        withdraw_req = schemata.WithdrawCallbackRequest(data)
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


def periodic_send_deposit():
    deposit_notification_endpoint = config['deposit_notification_endpoint']

    unacknowledged_transactions_q = transaction.CryptoDepositTransaction.query.filter(
        transaction.CryptoDepositTransaction.is_acknowledged.is_(False)
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

        withdraw_req = schemata.DepositCallbackRequest(data)
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
