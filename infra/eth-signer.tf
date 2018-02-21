data "template_file" "eth-signer" {
  count = 1

  template = <<JSON
[
  {
    "name": "eth-signer",
    "essential": true,
    "image": "docker.cryptology.com/payments/cryptopayment-daemon:${var.build_version}",
    "dnsSearchDomains": ["${var.project_name}-${terraform.workspace}"],
    "memoryReservation": 256,
    "command": ["python", "-u", "prod/eth_signer_runner.py"],
    "portMappings": [
      {
        "containerPort": 9001
      }
    ],
    "environment": [
      {
        "name": "DATABASE_URL",
        "value": "postgres://cryptopayments:${var.postgres_password}@postgres/cryptopayments"
      },
      {"name": "ETHERIUMD_URL", "value": "http://geth:8545"},
      {
        "name": "ETH_MASTERKEY_NAME",
        "value": "${var.eth_master_key_name}"
      },
      {
        "name": "ETH_MASTERKEY_PASSPHRASE",
        "value": "${var.eth_master_key_passphrase}"
      },
      {"name": "SENTRY_DSN", "value": "${var.sentry_dsn}"},
      {"name": "SENTRY_ENVIRONMENT", "value": "${terraform.workspace}"},
      {"name": "PORT", "value": "9001"}
    ],
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "${aws_cloudwatch_log_group.eth-signer.name}",
        "awslogs-region": "${var.aws_region}"
      }
    }
  }
]
JSON
}

resource "aws_cloudwatch_log_group" "eth-signer" {
  count             = 1
  name              = "${var.project_name}-${terraform.workspace}-eth-signer"
  retention_in_days = 7
}

resource "aws_ecs_task_definition" "eth-signer" {
  count                 = 1
  container_definitions = "${data.template_file.eth-signer.rendered}"
  family                = "${var.project_name}-${terraform.workspace}-eth-signer"
}

resource "aws_ecs_service" "eth-signer" {
  count = 1

  cluster                            = "${aws_ecs_cluster.main.id}"
  name                               = "eth-signer"
  task_definition                    = "${aws_ecs_task_definition.eth-signer.arn}"
  desired_count                      = "${var.enable_services * 1}"
  deployment_maximum_percent         = 200
  deployment_minimum_healthy_percent = 50

  iam_role = "${aws_iam_role.ecs_role.id}"

  load_balancer {
    target_group_arn = "${aws_alb_target_group.eth-signer.id}"
    container_name   = "eth-signer"
    container_port   = 9001
  }
}
