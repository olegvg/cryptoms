terraform {
  backend "s3" {
    bucket         = "cryptopayments-terraform-remote-state.cryptology.com"
    key            = "remote-state"
    dynamodb_table = "cryptopayments-terraform-remote-state"
    region         = "eu-central-1"
  }
}
