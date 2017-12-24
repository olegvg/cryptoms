#!/bin/bash

cd ./bitcoin

./autogen.sh

./configure --with-incompatible-bdb --with-gui=no --with-zmq

make -j 4

cd $OLDPWD