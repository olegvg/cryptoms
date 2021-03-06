from transer import config
from transer.btc import reconciliation


def reconcile_btc(enforce=False):
    btcd_instance_name = config['btcd_instance_name']
    return reconciliation.reconcile_addresses(bt_name=btcd_instance_name, enforce=enforce)
