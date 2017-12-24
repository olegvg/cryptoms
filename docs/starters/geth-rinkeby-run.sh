#!/bin/bash

cd ~/go-ethereum

#./build/bin/geth --rpc --debug --port 30304 --config /mnt/blockchain/ethereum-rinkeby-config.yml --bootnodes=enode://a24ac7c5484ef4ed0c5eb2d36620ba4e4aa13b8c84684e1b4aab0cebea2ae45cb4d375b77eab56516d34bfbd3c1a833fc51296ff084b770b94fb9028c4d25ccf@52.169.42.101:30303 init ../rinkeby.json
./build/bin/geth --rpc --debug --port 30304 --config /mnt/blockchain/ethereum-rinkeby-config.yml --bootnodes=enode://a24ac7c5484ef4ed0c5eb2d36620ba4e4aa13b8c84684e1b4aab0cebea2ae45cb4d375b77eab56516d34bfbd3c1a833fc51296ff084b770b94fb9028c4d25ccf@52.169.42.101:30303
 
cd $OLDPWD

