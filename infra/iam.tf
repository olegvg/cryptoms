resource "aws_iam_role" "ecs_role" {
  name               = "${var.project_name}-${terraform.workspace}"
  assume_role_policy = "${file("policies/ecs-role.json")}"
}

resource "aws_iam_role_policy" "ecs_service_role_policy" {
  name   = "${var.project_name}-service"
  policy = "${file("policies/ecs-service-role-policy.json")}"
  role   = "${aws_iam_role.ecs_role.id}"
}

resource "aws_iam_role_policy" "ecs_instance_role_policy" {
  name   = "${var.project_name}-instance"
  policy = "${file("policies/ecs-instance-role-policy.json")}"
  role   = "${aws_iam_role.ecs_role.id}"
}

resource "aws_iam_instance_profile" "ecs" {
  name = "${var.project_name}-${terraform.workspace}"
  path = "/"
  role = "${aws_iam_role.ecs_role.name}"
}
