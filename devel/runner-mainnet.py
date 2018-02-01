import os.path
import sys


if __name__ == '__main__':
    selfpath = os.path.dirname(os.path.abspath(__file__))
    rootpath = os.path.join(selfpath, '..')
    sys.path.append(rootpath)

    from transer import daemon

    daemon.run(
        db_uri='postgresql://ogaidukov@127.0.0.1:5432/btc_test',
        listen_host='0.0.0.0',
        listen_port=8000,
        workers=10,
        btc_masterkey_name='btc_main',
        eth_masterkey_name='eth_main',
        btcd_instance_name='main_instance',
        etcd_instance_uri='http://127.0.0.1:8545',
        deposit_notification_endpoint='https://staging.payments.cryptology.com/api/internal/cryptopay/deposit'
    )

