#!/bin/bash

gpg --encrypt --recipient terraform@cryptopayments --output=staging.vault staging.tfvars
