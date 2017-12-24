#!/bin/bash

cd ~/bitcoin

./src/bitcoind -printtoconsole -debug=db -debug=coindb -debug=rpc -datadir=/mnt/blockchain/bitcoin-testnet -conf=/mnt/blockchain/bitcoin-testnet.conf

cd $OLDPWD

