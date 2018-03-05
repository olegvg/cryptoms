#!/usr/bin/env python3

from pywallet import wallet
from pprint import pprint

seed = wallet.generate_mnemonic()
w = wallet.create_wallet(network="btctest", seed=seed, children=0)

pprint(w)
