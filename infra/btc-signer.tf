data "template_file" "btc-signer" {
  count = 1

  template = <<JSON
[
  {
    "name": "btc-signer",
    "essential": true,
    "image": "docker.cryptology.com/payments/cryptopayment-daemon:${var.build_version}",
    "dnsSearchDomains": ["${var.project_name}-${terraform.workspace}"],
    "memoryReservation": 256,
    "command": ["python", "-u", "prod/btc_signer_runner.py"],
    "portMappings": [
      {
        "containerPort": 9000
      }
    ],
    "environment": [
      {
        "name": "DATABASE_URL",
        "value": "postgres://cryptopayments:${var.postgres_password}@postgres/cryptopayments"
      },
      {
        "name": "BTC_MASTERKEY_NAME",
        "value": "${var.btc_master_key_name}"
      },
      {
        "name": "BTC_MASTERKEY_PASSPHRASE",
        "value": "${var.btc_master_key_passphrase}"
      },
      {"name": "BITCOIND_URL", "value": "http://${var.bitcoind_rpcuser}:${var.bitcoind_rpcpassword}@bitcoind:8332"},
      {"name": "SENTRY_DSN", "value": "${var.sentry_dsn}"},
      {"name": "SENTRY_ENVIRONMENT", "value": "${terraform.workspace}"},
      {"name": "PORT", "value": "9000"}
    ],
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "${aws_cloudwatch_log_group.btc-signer.name}",
        "awslogs-region": "${var.aws_region}"
      }
    }
  }
]
JSON
}

resource "aws_cloudwatch_log_group" "btc-signer" {
  count             = 1
  name              = "${var.project_name}-${terraform.workspace}-btc-signer"
  retention_in_days = 7
}

resource "aws_ecs_task_definition" "btc-signer" {
  count                 = 1
  container_definitions = "${data.template_file.btc-signer.rendered}"
  family                = "${var.project_name}-${terraform.workspace}-btc-signer"
}

resource "aws_ecs_service" "btc-signer" {
  count = 1

  cluster                            = "${aws_ecs_cluster.main.id}"
  name                               = "btc-signer"
  task_definition                    = "${aws_ecs_task_definition.btc-signer.arn}"
  desired_count                      = "${var.enable_services * 1}"
  deployment_maximum_percent         = 200
  deployment_minimum_healthy_percent = 50

  iam_role = "${aws_iam_role.ecs_role.id}"

  load_balancer {
    target_group_arn = "${aws_alb_target_group.btc-signer.id}"
    container_name   = "btc-signer"
    container_port   = 9000
  }
}
