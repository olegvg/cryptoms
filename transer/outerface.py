import json

from aiohttp.web import json_response

from transer.types import CryptoCurrency, WithdrawalStatus
from transer import schemata

from transer.orchestrator import withdraw, claim_wallet_addr


async def claim_wallet_addr_endpoint(request):
    currency = request.match_info['currency']

    # strange redundant validator :-)
    if currency not in [x.value for x in CryptoCurrency]:
        return json_response({'error': True, 'message': f'{currency} is wrong'})

    handlers = {
        CryptoCurrency.BITCOIN.value: claim_wallet_addr.claim_btc_addr,
        CryptoCurrency.ETHERIUM.value: claim_wallet_addr.claim_eth_addr
    }

    handler_func = handlers.get(currency, lambda **_: WithdrawalStatus.ERROR.name)

    status = handler_func()

    return json_response(status)


async def withdraw_endpoint(request):
    data = await request.json(loads=json.loads)
    withdraw_req = schemata.WithdrawRequest(data)
    withdraw_req.validate()

    handlers = {
        CryptoCurrency.BITCOIN.value: withdraw.withdraw_btc,
        CryptoCurrency.ETHERIUM.value: withdraw.withdraw_eth
    }

    handler_func = handlers.get(data['currency'], lambda **_: WithdrawalStatus.ERROR.name)

    status = handler_func(
        u_txid=withdraw_req.tx_id,
        address=withdraw_req.wallet_addr,
        amount=withdraw_req.amount
    )

    resp_data = {'tx_id': data['tx_id'], 'status': status}
    withdraw_req = schemata.WithdrawResponse(resp_data)
    withdraw_req.validate()
    return json_response(resp_data)


async def withdrawal_status_endpoint(request):
    crypto_transaction = request.match_info['u_txid']

    resp_data = {'tx_id': crypto_transaction, 'status': 'COMPLETED'}
    withdraw_req = schemata.WithdrawResponse(resp_data)
    withdraw_req.validate()
    return json_response(resp_data)
