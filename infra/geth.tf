data "template_file" "geth" {
  count = 1

  template = <<JSON
[
  {
    "name": "geth",
    "essential": true,
    "image": "ethereum/client-go:v1.8.1",
    "memoryReservation": 4096,
    "command": [
      "--rpc", "--syncmode", "full", "--debug", "--networkid=${var.geth_network_id}",
      "--rpcaddr", "0.0.0.0", "--rpcport", "8545", "--rpcvhosts", "geth",
      "--datadir", "/ethereum-data"
    ],
    "mountPoints": [
        {
          "sourceVolume": "ethereum-data",
          "containerPath": "/ethereum-data"
        }
    ],
    "portMappings": [
      {
        "containerPort": 8545
      }
    ],
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "${aws_cloudwatch_log_group.geth.name}",
        "awslogs-region": "${var.aws_region}"
      }
    }
  }
]
JSON
}

resource "aws_cloudwatch_log_group" "geth" {
  count             = 1
  name              = "${var.project_name}-${terraform.workspace}-geth"
  retention_in_days = 7
}

resource "aws_ecs_task_definition" "geth" {
  count                 = 1
  volume {
    name = "ethereum-data"
    host_path = "/mnt/blockchain-data/ethereum"
  }
  container_definitions = "${data.template_file.geth.rendered}"
  family                = "${var.project_name}-${terraform.workspace}-geth"
}

resource "aws_ecs_service" "geth" {
  count = 1

  cluster                            = "${aws_ecs_cluster.main.id}"
  name                               = "geth"
  task_definition                    = "${aws_ecs_task_definition.geth.arn}"
  desired_count                      = "${var.enable_services * 1}"
  deployment_maximum_percent         = 100
  deployment_minimum_healthy_percent = 0

  iam_role = "${aws_iam_role.ecs_role.id}"

  load_balancer {
    target_group_arn = "${aws_alb_target_group.geth.id}"
    container_name   = "geth"
    container_port   = 8545
  }
}
