# transer
Набор утилит для проведения транзакций в сетях Bitcoin и Ethereum

## Референсный deploy
`cd ~`

`git clone git://...distr transer`

Сделать virtualenv with python 3.6, установить build-essentials и прочие либы-зависимости 

`pip install -r transer/requirements.txt`

`cd transer`

`python setup.py bdist_wheel`

`cd ..`

`pip install pip install transer/dist/transer_btc-0.1-py3-none-any.whl`


`mkdir /mnt/blockchain/bitcoin`

`mkdir /mnt/blockchain/bitcoin-testnet`

`mkdir /mnt/blockchain/ethereum`

`mkdir /mnt/blockchain/ethereum-rinkeby`

`mkdir /mnt/blockchain/ethereum-ropsten`

### Референсные скрипты установки и запуска

`cp transer/docs/starters/* .`

`cp transer/docs/configs/* /mnt/blockchain`

### Bitcoind
`git clone https://github.com/bitcoin/bitcoin`

`./bitcoin-build.sh`

Запустить боевой 'bitcoind'

`./bitcoin-run.sh`

## БД Postgresql для bitcoin

Смотри [DDL](docs/ddl.sql) для инициализации схем.

### Ethereum
`git clone https://github.com/ethereum/go-ethereum`

`./geth-build.sh`

Запустить боевой 'geth'

`./geth-run.sh`

### Демон

`transer`
