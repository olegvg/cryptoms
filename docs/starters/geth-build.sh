#!/bin/bash

cd ./go-ethereum

make -j 4 geth

cd $OLDPWD