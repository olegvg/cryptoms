from functools import partial
from os import environ
from concurrent import futures
import asyncio
from aiohttp import web

from transer.utils import handler_fabric, init_db, create_delayed_scheduler, dump_db_ddl, recreate_entire_database
from transer.exceptions import DaemonConfigException
from transer.btc import init_btc
from transer.eth import init_eth
from transer.orchestrator import deposit, withdraw

from transer import outerface
from transer import config


def run(db_uri, listen_host, listen_port, workers,
        btc_masterkey_name, eth_masterkey_name,
        btc_crypt_key, eth_crypt_key,
        btcd_instance_name, ethd_instance_uri,
        btc_signing_instance_uri, eth_signing_instance_uri,
        deposit_notification_endpoint, withdraw_notification_endpoint):

    config['eth_masterkey_name'] = eth_masterkey_name
    config['btc_masterkey_name'] = btc_masterkey_name

    config['eth_crypt_key'] = eth_crypt_key
    config['btc_crypt_key'] = btc_crypt_key

    config['ethd_instance_uri'] = ethd_instance_uri
    config['btcd_instance_name'] = btcd_instance_name

    config['eth_signing_instance_uri'] = eth_signing_instance_uri
    config['btc_signing_instance_uri'] = btc_signing_instance_uri

    config['deposit_notification_endpoint'] = deposit_notification_endpoint
    config['withdraw_notification_endpoint'] = withdraw_notification_endpoint
    #
    # # TODO do refactoring to mitigate the circular dependencies
    # from transer.orchestrator import deposit, withdraw
    # from transer import outerface

    async_loop = asyncio.get_event_loop()
    app = web.Application()

    init_db(db_uri)
    btc_dispatcher = init_btc()      # gather JSON-RPC interfaces of Bitcoin processor
    eth_dispatcher = init_eth()      # gather JSON-RPC interfaces of Ethereum processor

    executor = futures.ProcessPoolExecutor(max_workers=workers)

    app.router.add_post('/btc', handler_fabric(executor, btc_dispatcher))
    app.router.add_post('/eth', handler_fabric(executor, eth_dispatcher))
    app.router.add_post('/claim-wallet-addr/{currency}', outerface.claim_wallet_addr_endpoint)
    app.router.add_post('/reconcile/{currency}', outerface.reconcile_addresses_endpoint)
    app.router.add_post('/enforce-reconcile/{currency}', partial(outerface.reconcile_addresses_endpoint, enforce=True))
    app.router.add_post('/withdraw', outerface.withdraw_endpoint)
    app.router.add_get('/withdrawal-status/{u_txid}', outerface.withdrawal_status_endpoint)

    delayed_scheduler = create_delayed_scheduler(loop=async_loop, executor=executor)

    btc_deposit_monitor_task = delayed_scheduler(
        deposit.periodic_check_deposit_btc,
        interval=50
    )

    eth_deposit_monitor_task = delayed_scheduler(
        deposit.periodic_check_deposit_eth,
        interval=50
    )

    deposit_send_task = delayed_scheduler(
        outerface.periodic_send_deposit,
        interval=50
    )

    btc_withdraw_monitor_task = delayed_scheduler(
        withdraw.periodic_check_withdraw_btc,
        interval=50
    )

    eth_withdraw_monitor_task = delayed_scheduler(
        withdraw.periodic_check_withdraw_eth,
        interval=50
    )

    withdraw_send_task = delayed_scheduler(
        outerface.periodic_send_withdraw,
        interval=50
    )

    web.run_app(app, host=listen_host, port=listen_port, loop=async_loop)


def main():
    try:
        btc_masterkey_name = environ['T_BTC_MASTERKEY_NAME']
        eth_masterkey_name = environ['T_ETH_MASTERKEY_NAME']

        if btc_masterkey_name:
            btc_crypt_key = input(f"Enter the deciphering password for private key'{btc_masterkey_name}': ")
            btc_crypt_key_2 = input('Enter it again: ')
            if btc_crypt_key != btc_crypt_key_2:
                raise DaemonConfigException(f'cannot decipher key {btc_masterkey_name}')
        else:
            btc_crypt_key = 'Snake oil'

        if eth_masterkey_name:
            eth_crypt_key = input(f"Enter the deciphering password for private key'{eth_masterkey_name}': ")
            eth_crypt_key_2 = input('Enter it again: ')
            if eth_crypt_key != eth_crypt_key_2:
                raise DaemonConfigException(f'cannot decipher key {eth_masterkey_name}')
        else:
            eth_crypt_key = 'Snake oil'

        btc_signing_instance_uri = environ['T_BTC_SIGNING_INSTANCE_URI']
        eth_signing_instance_uri = environ['T_ETH_SIGNING_INSTANCE_URI']

        btcd_instance_name = environ['T_BTCD_INSTANCE_NAME']
        ethd_instance_uri = environ['T_ETHD_INSTANCE_URI']
        deposit_notification_endpoint = environ['T_DEPOSIT_NOTIFICATION_ENDPOINT']
        withdraw_notification_endpoint = environ['T_WITHDRAW_NOTIFICATION_ENDPOINT']

        db_uri = environ['T_DB_URI']
        listen_host = environ['T_LISTEN_HOST']
        listen_port = int(environ['T_LISTEN_PORT'])
        workers = environ['WORKERS']
    except KeyError as e:
        raise DaemonConfigException("Config env vars don't set properly. Can't start.") from e

    run(
        db_uri=db_uri,
        listen_host=listen_host,
        listen_port=listen_port,
        workers=workers,
        btc_masterkey_name=btc_masterkey_name,
        eth_masterkey_name=eth_masterkey_name,
        btc_crypt_key=btc_crypt_key,
        eth_crypt_key=eth_crypt_key,
        btcd_instance_name=btcd_instance_name,
        ethd_instance_uri=ethd_instance_uri,
        btc_signing_instance_uri=btc_signing_instance_uri,
        eth_signing_instance_uri=eth_signing_instance_uri,
        deposit_notification_endpoint=deposit_notification_endpoint,
        withdraw_notification_endpoint=withdraw_notification_endpoint
    )
