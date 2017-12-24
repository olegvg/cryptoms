#!/bin/bash

cd ~/go-ethereum

./build/bin/geth --rpc --debug --port 30301 --config /mnt/blockchain/ethereum-config.yml

cd $OLDPWD

