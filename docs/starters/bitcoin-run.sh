#!/bin/bash

cd ~/bitcoin

./src/bitcoind -printtoconsole -debug=db -debug=coindb -debug=rpc -datadir=/mnt/blockchain/bitcoin -conf=/mnt/blockchain/bitcoin.conf

cd $OLDPWD

