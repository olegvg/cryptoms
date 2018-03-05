data "template_file" "pull" {
  template = <<JSON
[
  {
    "name": "pull",
    "essential": true,
    "image": "docker.cryptology.com/payments/cryptopayment-daemon:${var.build_version}",
    "command": ["true"],
    "memoryReservation": 128
  }
]
JSON
}

resource "aws_ecs_task_definition" "pull" {
  container_definitions = "${data.template_file.pull.rendered}"
  family                = "${var.project_name}-${terraform.workspace}-pull"
}
