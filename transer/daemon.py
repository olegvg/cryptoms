from functools import partial
from concurrent import futures
import asyncio
from aiohttp import web
from raven import breadcrumbs

from transer.utils import handler_fabric, endpoint_fabric, init_db, init_logging, create_delayed_scheduler
from transer.utils import dump_db_ddl, recreate_entire_database
from transer.exceptions import DaemonConfigException
from transer.btc import init_btc
from transer.eth import init_eth
from transer import config


def run(db_uri, listen_host, listen_port, workers, signing_mode,
        btc_masterkey_name, eth_masterkey_name,
        btc_crypt_key, eth_crypt_key,
        btcd_instance_uri, ethd_instance_uri,
        btc_signing_instance_uri, eth_signing_instance_uri,
        deposit_notification_endpoint, withdraw_notification_endpoint,
        sentry_dsn, app_release, sentry_environment):

    config['eth_masterkey_name'] = eth_masterkey_name
    config['btc_masterkey_name'] = btc_masterkey_name

    config['eth_crypt_key'] = eth_crypt_key
    config['btc_crypt_key'] = btc_crypt_key

    config['ethd_instance_uri'] = ethd_instance_uri
    config['btcd_instance_uri'] = btcd_instance_uri
    config['btcd_instance_name'] = 'fake_instance'

    config['eth_signing_instance_uri'] = eth_signing_instance_uri
    config['btc_signing_instance_uri'] = btc_signing_instance_uri

    config['deposit_notification_endpoint'] = deposit_notification_endpoint
    config['withdraw_notification_endpoint'] = withdraw_notification_endpoint

    config['sentry_dsn'] = sentry_dsn
    config['app_release'] = app_release
    config['sentry_environment'] = sentry_environment
    init_logging()

    breadcrumbs.record(message='Initial config', data=config,
                       category='config', level='info')

    # TODO do refactoring to mitigate the circular dependencies
    from transer.orchestrator import deposit, withdraw
    from transer import outerface

    async_loop = asyncio.get_event_loop()
    app = web.Application()

    init_db(db_uri)

    # greasy hack :-))
    from transer.db import btc, sqla_session
    from sqlalchemy.orm.exc import NoResultFound
    bitcoind_instance_q = btc.BitcoindInstance.query.filter(
        btc.BitcoindInstance.instance_name == 'fake_instance'
    )
    try:
        bitcoind_instance_q.one()
    except NoResultFound:
        fake_inst = btc.BitcoindInstance(instance_name='fake_instance')
        sqla_session.add(fake_inst)
        sqla_session.commit()
    sqla_session.close()
    # end of greasy hack

    btc_dispatcher = init_btc()      # gather JSON-RPC interfaces of Bitcoin processor
    eth_dispatcher = init_eth()      # gather JSON-RPC interfaces of Ethereum processor

    process_executor = futures.ProcessPoolExecutor(max_workers=workers)

    # We need 'ThreadPoolExecutor' because 'multiprocessing' cannot pickle sockets
    thread_executor = futures.ThreadPoolExecutor(max_workers=workers)

    app.router.add_post('/btc', handler_fabric(process_executor, btc_dispatcher))
    app.router.add_post('/eth', handler_fabric(process_executor, eth_dispatcher))

    app.router.add_post(
        '/claim-wallet-addr/{currency}',
        endpoint_fabric(thread_executor, outerface.claim_wallet_addr_endpoint)
    )
    app.router.add_post(
        '/reconcile/{currency}',
        endpoint_fabric(thread_executor, outerface.reconcile_addresses_endpoint)
    )
    app.router.add_post(
        '/enforce-reconcile/{currency}',
        endpoint_fabric(thread_executor, partial(outerface.reconcile_addresses_endpoint, enforce=True))
    )
    app.router.add_post(
        '/withdraw',
        endpoint_fabric(thread_executor, outerface.withdraw_endpoint)
    )
    app.router.add_get(
        '/withdrawal-status/{u_txid}',
        endpoint_fabric(thread_executor, outerface.withdrawal_status_endpoint)
    )

    delayed_scheduler = create_delayed_scheduler(loop=async_loop, executor=process_executor)

    # suppress all the outgoing connections/notification clients in 'signing node' mode
    if signing_mode is False:
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
