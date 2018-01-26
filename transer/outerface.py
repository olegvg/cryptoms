import json

from aiohttp.web import json_response

from transer.types import CryptoCurrency, WithdrawalStatus
from transer import config, schemata
from transer.db import btc, eth

from transer.orchestrator import withdraw


async def claim_wallet_addr(request):
    currency = request.match_info['currency']

    # strange redundant validator :-)
    if currency not in [x.value for x in CryptoCurrency]:
        return json_response({'error': True, 'message': f'{currency} is wrong'})

    # TODO refactor code and move it to orchestrator package
    if currency == 'ETH':
        key_name = config['eth_masterkey_name']
        masterkey_q = eth.MasterKey.query.filter(
            eth.MasterKey.masterkey_name == key_name
        )
        masterkey = masterkey_q.one()

        address_row = eth.Address.create_next_address(masterkey=masterkey)

        data = {'wallet_address': address_row.address}

        # another strange redundant validator :-)
        new_wallet_response = schemata.ClaimWalletAddressResponse(data)
        new_wallet_response.validate()

        return json_response(data)

    # TODO refactor code and move it to orchestrator package
    if currency == 'BTC':
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

        address_row = btc.Address.create_next_address(bitcoind_inst=bitcoind_inst, masterkey=masterkey)

        data = {'wallet_address': address_row.address}

        # another strange redundant validator :-)
        new_wallet_response = schemata.ClaimWalletAddressResponse(data)
        new_wallet_response.validate()

        return json_response(data)


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


async def withdrawal_status(request):
    crypto_transaction = request.match_info['u_txid']

    resp_data = {'tx_id': crypto_transaction, 'status': 'COMPLETED'}
    withdraw_req = schemata.WithdrawResponse(resp_data)
    withdraw_req.validate()
    return json_response(resp_data)
