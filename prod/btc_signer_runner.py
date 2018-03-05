import os.path
import sys
from os import environ

from raven import Client

if __name__ == '__main__':
    selfpath = os.path.dirname(os.path.abspath(__file__))
    rootpath = os.path.join(selfpath, '..')
    sys.path.append(rootpath)

    from transer import daemon
    from transer.exceptions import DaemonConfigException

    sentry_dsn = None
    try:
        db_uri = environ['DATABASE_URL']
        listen_port = int(environ['PORT'])
        workers = int(environ.get('WORKERS', 10))

        signing_mode = True

        btc_masterkey_name = environ['BTC_MASTERKEY_NAME']
        btc_crypt_key = environ.get('BTC_MASTERKEY_PASSPHRASE', 'Snake oil')

        eth_masterkey_name = ''
        eth_crypt_key = ''

        btc_signing_instance_uri = f'http://127.0.0.1:{listen_port}/btc'
        eth_signing_instance_uri = f'http://127.0.0.1:{listen_port}/eth'

        btcd_instance_uri = environ['BITCOIND_URL']
        ethd_instance_uri = ''
        deposit_notification_endpoint = ''
        withdraw_notification_endpoint = ''

        sentry_dsn = os.environ.get("SENTRY_DSN", None)
        app_release = os.environ.get("APP_VERSION", "local_commit")
        sentry_environment = os.environ.get("SENTRY_ENVIRONMENT", "local")

    except KeyError as e:
        if sentry_dsn:
            sentry_client = Client(dsn=sentry_dsn)
            sentry_client.captureException()
        raise DaemonConfigException("Config env vars don't set properly. Can't start.") from e

    daemon.run(
        db_uri=db_uri,
        listen_host='0.0.0.0',
        listen_port=listen_port,
        workers=workers,
        signing_mode=signing_mode,
        btc_masterkey_name=btc_masterkey_name,
        eth_masterkey_name=eth_masterkey_name,
        btc_crypt_key=btc_crypt_key,
        eth_crypt_key=eth_crypt_key,
        ethd_instance_uri=ethd_instance_uri,
        btcd_instance_uri=btcd_instance_uri,
        btc_signing_instance_uri=btc_signing_instance_uri,
        eth_signing_instance_uri=eth_signing_instance_uri,
        deposit_notification_endpoint=deposit_notification_endpoint,
        withdraw_notification_endpoint=withdraw_notification_endpoint,
        sentry_dsn=sentry_dsn,
        app_release=app_release,
        sentry_environment=sentry_environment
    )
