data "template_file" "bitcoind" {
  count = 1

  template = <<JSON
[
  {
    "name": "bitcoind",
    "essential": true,
    "image": "docker.cryptology.com/blockchain/bitcoind:v4",
    "memoryReservation": 4096,
    "mountPoints": [
        {
          "sourceVolume": "bitcoin-data",
          "containerPath": "/bitcoin"
        }
    ],
    "portMappings": [
      {
        "containerPort": 8332
      }
    ],
    "environment": [
      {
        "name": "TESTNET",
        "value": "${var.bitcoind_testnet}"
      },
      {
        "name": "RPCUSER",
        "value": "${var.bitcoind_rpcuser}"
      },
      {
        "name": "RPCPASSWORD",
        "value": "${var.bitcoind_rpcpassword}"
      },
      {
        "name": "DISABLEWALLET",
        "value": "0"
      }
    ],
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "${aws_cloudwatch_log_group.bitcoind.name}",
        "awslogs-region": "${var.aws_region}"
      }
    }
  }
]
JSON
}

resource "aws_cloudwatch_log_group" "bitcoind" {
  count             = 1
  name              = "${var.project_name}-${terraform.workspace}-bitcoind"
  retention_in_days = 7
}

resource "aws_ecs_task_definition" "bitcoind" {
  count                 = 1
  container_definitions = "${data.template_file.bitcoind.rendered}"
  volume {
    name = "bitcoin-data"
    host_path = "/mnt/blockchain-data/bitcoin"
  }
  family                = "${var.project_name}-${terraform.workspace}-bitcoind"
}

resource "aws_ecs_service" "bitcoind" {
  count = 1

  cluster                            = "${aws_ecs_cluster.main.id}"
  name                               = "bitcoind"
  task_definition                    = "${aws_ecs_task_definition.bitcoind.arn}"
  desired_count                      = "${var.enable_services * 1}"
  deployment_maximum_percent         = 100
  deployment_minimum_healthy_percent = 0

  iam_role = "${aws_iam_role.ecs_role.id}"

  load_balancer {
    target_group_arn = "${aws_alb_target_group.bitcoind.id}"
    container_name   = "bitcoind"
    container_port   = 8332
  }
}
