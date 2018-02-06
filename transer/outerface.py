import json
from functools import partial

from jsonrpc.utils import DatetimeDecimalEncoder

from aiohttp.web import json_response, Response

from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound

from transer import schemata
from transer.db import transaction, sqla_session
from transer.types import CryptoCurrency, WithdrawalStatus

from transer.orchestrator import withdraw, claim_wallet_addr, reconciliation


async def claim_wallet_addr_endpoint(request):
    currency = request.match_info['currency']

    # strange redundant validator :-)
    if currency not in [x.value for x in CryptoCurrency]:
        resp = Response()
        resp.set_status(404, f'Crypto currency ticker {currency} is not supported')
        return resp

    handlers = {
        CryptoCurrency.BITCOIN.value: claim_wallet_addr.claim_btc_addr,
        CryptoCurrency.ETHERIUM.value: claim_wallet_addr.claim_eth_addr
    }

    handler_func = handlers.get(currency, lambda **_: WithdrawalStatus.FAILED.value)

    status = handler_func()

    if status == WithdrawalStatus.FAILED.value:
        resp = Response()
        resp.set_status(404, f'Allocation of new address unsuccessful')
        return resp

    return json_response(status)


async def reconcile_addresses_endpoint(request, enforce=False):
    currency = request.match_info['currency']

    # strange redundant validator :-)
    if currency not in [x.value for x in CryptoCurrency]:
        resp = Response()
        resp.set_status(404, f'Crypto currency ticker {currency} is not supported')
        return resp

    handlers = {
        CryptoCurrency.BITCOIN.value: reconciliation.reconcile_btc,
    }

    handler_func = handlers.get(currency, lambda **_: WithdrawalStatus.FAILED)
    res = handler_func(enforce=enforce)

    if res == WithdrawalStatus.FAILED:
        resp = Response()
        resp.set_status(404, f'Reconciliation is unsuccessful')
        return resp

    dumps = partial(json.dumps, cls=DatetimeDecimalEncoder)
    return json_response({'actual_balances': res}, dumps=dumps)


async def withdraw_endpoint(request):
    data = await request.json(loads=json.loads)
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

    if status == WithdrawalStatus.FAILED.value:
        resp = Response()
        resp.set_status(404, f'Withdrawal transaction ends unsuccessfully')
        return resp

    resp_data = {'tx_id': data['tx_id'], 'status': status}
    withdraw_req = schemata.WithdrawResponse(resp_data)
    withdraw_req.validate()
    return json_response(resp_data)


async def withdrawal_status_endpoint(request):
    u_txid = request.match_info['u_txid']

    crypto_transaction_q = transaction.CryptoWithdrawTransaction.query.filter(
        transaction.CryptoWithdrawTransaction.u_txid == u_txid
    )

    try:
        crypto_transaction = crypto_transaction_q.one()
    except NoResultFound:
        resp = Response()
        resp.set_status(404, f'Transaction {u_txid} is not found')
        return resp

    handlers = {
        CryptoCurrency.BITCOIN.value: withdraw.withdrawal_status_btc,
        CryptoCurrency.ETHERIUM.value: withdraw.withdrawal_status_eth
    }
    handler_func = handlers.get(crypto_transaction.currency, lambda **_: WithdrawalStatus.FAILED.value)

    handler_func(crypto_transaction)

    sqla_session.commit()

    if crypto_transaction.status == WithdrawalStatus.FAILED.value:
        resp = Response()
        resp.set_status(404, f'Checking of transaction status ends unsuccessfully')
        return resp

    resp_data = {'tx_id': u_txid, 'status': crypto_transaction.status}
    withdraw_req = schemata.WithdrawResponse(resp_data)
    withdraw_req.validate()
    return json_response(resp_data)
