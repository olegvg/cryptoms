data "template_file" "daemon" {
  count = 1

  template = <<JSON
[
  {
    "name": "daemon",
    "essential": true,
    "image": "docker.cryptology.com/payments/cryptopayment-daemon:${var.build_version}",
    "dnsSearchDomains": ["${var.project_name}-${terraform.workspace}"],
    "memoryReservation": 256,
    "portMappings": [
      {
        "containerPort": 8080
      }
    ],
    "environment": [
      {
        "name": "DATABASE_URL",
        "value": "postgres://cryptopayments:${var.postgres_password}@postgres/cryptopayments"
      },
      {"name": "BITCOIND_URL", "value": "http://${var.bitcoind_rpcuser}:${var.bitcoind_rpcpassword}@bitcoind:8332"},
      {"name": "ETHEREUMD_URL", "value": "http://geth:8545"},
      {"name": "CALLBACK_API_ROOT", "value": "${var.callback_api_root}"},
      {"name": "BTC_SIGNER_URL", "value": "http://btc-signer:9000/btc"},
      {"name": "ETH_SIGNER_URL", "value": "http://eth-signer:9001/eth"},
      {"name": "SENTRY_DSN", "value": "${var.sentry_dsn}"},
      {"name": "SENTRY_ENVIRONMENT", "value": "${terraform.workspace}"},
      {"name": "PORT", "value": "8080"},
      {"name": "BTC_MASTERKEY_NAME", "value": "${var.btc_master_key_name}"},
      {"name": "BTC_MASTERKEY_PASSPHRASE", "value": "${var.btc_master_key_passphrase}"},
      {"name": "ETH_MASTERKEY_NAME", "value": "${var.eth_master_key_name}"},
      {"name": "ETH_MASTERKEY_PASSPHRASE", "value": "${var.eth_master_key_passphrase}"}
    ],
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "${aws_cloudwatch_log_group.daemon.name}",
        "awslogs-region": "${var.aws_region}"
      }
    }
  }
]
JSON
}

resource "aws_cloudwatch_log_group" "daemon" {
  count             = 1
  name              = "${var.project_name}-${terraform.workspace}-daemon"
  retention_in_days = 7
}

resource "aws_ecs_task_definition" "daemon" {
  count                 = 1
  container_definitions = "${data.template_file.daemon.rendered}"
  family                = "${var.project_name}-${terraform.workspace}-daemon"
}

resource "aws_ecs_service" "daemon" {
  count = 1

  cluster                            = "${aws_ecs_cluster.main.id}"
  name                               = "daemon"
  task_definition                    = "${aws_ecs_task_definition.daemon.arn}"
  desired_count                      = "${var.enable_services * 1}"
  deployment_maximum_percent         = 200
  deployment_minimum_healthy_percent = 50

  iam_role = "${aws_iam_role.ecs_role.id}"

  load_balancer {
    target_group_arn = "${aws_alb_target_group.webapp.id}"
    container_name   = "daemon"
    container_port   = 8080
  }
}
