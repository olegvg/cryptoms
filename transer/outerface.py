import json

from aiohttp.web import json_response

from transer.types import CryptoCurrency
from transer import config, schemata
from transer.db import btc, eth


async def claim_wallet_addr(request):
    currency = request.match_info['currency']
    if currency not in [x.value for x in CryptoCurrency]:
        return json_response({'error': True, 'message': f'{currency} is wrong'})

    if currency == 'ETH':
        key_name = config['eth_masterkey_name']
        masterkey_q = eth.MasterKey.query.filter(
            eth.MasterKey.masterkey_name == key_name
        )
        masterkey = masterkey_q.one()

        address_row = eth.Address.create_next_address(masterkey)

        data = {'wallet_address': address_row.address}

        new_wallet_response = schemata.ClaimWalletAddressResponse(data)
        new_wallet_response.validate()

        return json_response(data)

    if currency == 'BTC':
        key_name = config['btc_masterkey_name']
        masterkey_q = eth.MasterKey.query.filter(
            eth.MasterKey.masterkey_name == key_name
        )
        masterkey = masterkey_q.one()

        address_row = btc.Address.create_next_address(masterkey)

        data = {'wallet_address': address_row.address}

        new_wallet_response = schemata.ClaimWalletAddressResponse(data)
        new_wallet_response.validate()

        return json_response(data)
