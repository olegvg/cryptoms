resource "aws_security_group" "ecs" {
  vpc_id      = "${aws_vpc.main.id}"
  name        = "${var.project_name}-${terraform.workspace}-ecs"
  description = "${var.project_name}-${terraform.workspace}-ecs"

  lifecycle {
    create_before_destroy = true
  }

  tags {
    Role = "ecs"
    Env  = "${terraform.workspace}"
  }

  ingress {
    from_port = 0
    to_port   = 0
    protocol  = -1

    security_groups = [
      "${aws_security_group.alb.id}",
    ]
  }

  ingress {
    from_port = 22
    to_port   = 22
    protocol  = "tcp"

    cidr_blocks = [
      "0.0.0.0/0",
    ]
  }

  egress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"

    cidr_blocks = [
      "0.0.0.0/0",
    ]
  }
}

resource "aws_security_group" "alb" {
  vpc_id      = "${aws_vpc.main.id}"
  name        = "${var.project_name}-${terraform.workspace}-alb"
  description = "${var.project_name}-${terraform.workspace}-alb"

  lifecycle {
    create_before_destroy = true
  }

  tags {
    Role = "elb"
    Name = "${var.project_name}-${terraform.workspace}"
    Env  = "${terraform.workspace}"
  }

  egress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"

    cidr_blocks = [
      "${aws_subnet.main.*.cidr_block}",
    ]
  }

  ingress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"

    cidr_blocks = [
      "${aws_subnet.main.*.cidr_block}",
    ]
  }

  ingress {
    from_port = 8080
    to_port   = 8080
    protocol  = "tcp"

    cidr_blocks = [
      "0.0.0.0/0",
    ]
  }
}

resource "aws_security_group" "postgres" {
  name        = "${var.project_name}-${terraform.workspace}-postgres"
  description = "${var.project_name}-${terraform.workspace}-postgres"
  vpc_id      = "${aws_vpc.main.id}"

  lifecycle {
    create_before_destroy = true
  }

  tags {
    Role = "postgres"
    Name = "${var.project_name}-${terraform.workspace}"
    Env  = "${terraform.workspace}"
  }

  ingress {
    from_port = 5432
    to_port   = 5432
    protocol  = "tcp"

    security_groups = [
      "${aws_security_group.ecs.id}",
    ]
  }

  ingress {
    from_port = 5432
    protocol  = "tcp"
    to_port   = 5432

    cidr_blocks = [
      "87.118.201.244/32",
    ] # office ip
  }
}
