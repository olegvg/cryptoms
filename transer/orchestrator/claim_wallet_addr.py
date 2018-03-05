from transer import config, schemata
from transer.db import btc, eth
from transer.btc import create_address as btc_create_address


def claim_btc_addr():
    btcd_instance_name = config['btcd_instance_name']
    key_name = config['btc_masterkey_name']

    newborn_address = btc_create_address.create_unpropagated_address(
        bt_name=btcd_instance_name,
        key_name=key_name
    )

    btc_create_address.propdagate_bitcoind_with_address(    # exception raised if unsuccess
        bt_name=btcd_instance_name,
        address=newborn_address
    )

    data = {'wallet_address': newborn_address}

    # another strange redundant validator :-)
    new_wallet_response = schemata.ClaimWalletAddressResponse(data)
    new_wallet_response.validate()

    return data


def claim_eth_addr():
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

    return data
