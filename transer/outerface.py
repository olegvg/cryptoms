from aiohttp.web import json_response

from transer.types import CryptoCurrency
from transer import config, schemata
from transer.db import btc, eth


async def claim_wallet_addr(request):
    currency = request.match_info['currency']

    # strange redundant validator :-)
    if currency not in [x.value for x in CryptoCurrency]:
        return json_response({'error': True, 'message': f'{currency} is wrong'})

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
