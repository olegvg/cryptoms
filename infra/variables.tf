# Common vars
variable "project_name" {
  default = "cryptopay"
}

variable "enable_services" {
  default = true
}

# AWS vars
variable "aws_region" {
  default = "eu-central-1"
}

variable "aws_zones" {
  default = "a,b"
}

variable "aws_key_pair_name" {}

# Postgres vars
variable "postgres_password" {}

# webapp vars
variable "webapp_domain" {}

variable "eth_master_key_name" {}
variable "eth_master_key_passphrase" {}

variable "btc_master_key_name" {}
variable "btc_master_key_passphrase" {}

# Docker vars
variable "docker_registry_login" {}

variable "docker_registry_password" {}
variable "sentry_dsn" {}
variable "callback_api_root" {}

variable "build_version" {
  default = "latest"
}

variable "bitcoind_testnet" {}
variable "bitcoind_rpcuser" {}
variable "bitcoind_rpcpassword" {}

variable "geth_network_id" {
  # 4 - testnet  # 0 - mainnet
}
