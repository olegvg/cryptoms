#!/bin/bash

cd ~/go-ethereum

./build/bin/geth --rpc --debug --port 30303 --config /mnt/blockchain/ethereum-ropsten-config.yml

cd $OLDPWD

