import os.path
import sys


if __name__ == '__main__':
    selfpath = os.path.dirname(os.path.abspath(__file__))
    rootpath = os.path.join(selfpath, '..', 'transer')
    sys.path.append(rootpath)

    from transer import daemon

    daemon.run(
        db_uri='postgresql://ogaidukov@127.0.0.1:5432/btc_test',
        listen_host='0.0.0.0',
        listen_port=8000,
        workers=10,
        signing_mode=False,
        btc_masterkey_name='btc_test',
        eth_masterkey_name='eth_test',
        btc_crypt_key='1qazxsw2',
        eth_crypt_key='1qazxsw2',
        btcd_instance_uri='http://dummy:dummy@127.0.0.1:8332',
        ethd_instance_uri='http://127.0.0.1:48545',
        btc_signing_instance_uri='http://127.0.0.1:8000/btc',
        eth_signing_instance_uri='http://127.0.0.1:8000/eth',
        deposit_notification_endpoint='https://staging.payments.cryptology.com/api/internal/cryptopay/deposit',
        withdraw_notification_endpoint='https://staging.payments.cryptology.com/api/internal/cryptopay/withdraw',
        sentry_dsn=None,
        app_release=None,
        sentry_environment=None
    )
