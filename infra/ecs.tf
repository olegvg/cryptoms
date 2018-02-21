data "aws_ami" "ecs" {
  most_recent = true

  owners = [
    "amazon",
  ]

  filter {
    name = "name"

    values = [
      "*-amazon-ecs-optimized",
    ]
  }
}

resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-${terraform.workspace}"
}

data "template_file" "userdata" {
  template = "${file("userdata.tpl")}"

  vars {
    cluster_name         = "${aws_ecs_cluster.main.name}"
    docker_registry_auth = "${base64encode(join(":", list(var.docker_registry_login, var.docker_registry_password)))}"
  }
}

resource "aws_launch_configuration" "ecs" {
  name_prefix                 = "${var.project_name}-${terraform.workspace}-ecs-"
  image_id                    = "${data.aws_ami.ecs.image_id}"
  instance_type               = "m4.xlarge"
  iam_instance_profile        = "${aws_iam_instance_profile.ecs.id}"
  user_data                   = "${data.template_file.userdata.rendered}"
  associate_public_ip_address = true
  key_name                    = "${var.aws_key_pair_name}"
  ebs_optimized = true

  # Todo: create extra (non-root) volume for blockchain nodes
  root_block_device {
    volume_type = "standard"
    volume_size = "1000"
    delete_on_termination = false
  }

  security_groups = [
    "${aws_security_group.ecs.id}",
  ]

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_autoscaling_group" "ecs" {
  name                 = "${var.project_name}-${terraform.workspace}"
  launch_configuration = "${aws_launch_configuration.ecs.id}"

  vpc_zone_identifier = [
    "${aws_subnet.main.*.id}",
  ]

  min_size          = 0
  max_size          = 1
  desired_capacity  = 1
  health_check_type = "EC2"
  force_delete      = true

  tag {
    key                 = "env"
    value               = "${terraform.workspace}"
    propagate_at_launch = true
  }

  lifecycle {
    create_before_destroy = true
  }
}
