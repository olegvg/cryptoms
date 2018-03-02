resource "aws_alb" "webapp" {
  count = 1
  name  = "${var.project_name}-${terraform.workspace}-webapp"

  subnets = [
    "${aws_subnet.main.*.id}",
  ]

  internal = false

  security_groups = [
    "${aws_security_group.alb.id}",
  ]
}

resource "aws_alb_target_group" "webapp" {
  count = 1

  depends_on = [
    "aws_alb.webapp",
  ]

  name                 = "${var.project_name}-${terraform.workspace}-webapp"
  port                 = 8080
  protocol             = "HTTP"
  vpc_id               = "${aws_vpc.main.id}"
  deregistration_delay = 5

  # TODO: make real heartbeat handle
  health_check {
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 10
    matcher             = "404"
    path                = "/"
  }
}

resource "aws_alb_listener" "webapp" {
  count = 1

  load_balancer_arn = "${aws_alb.webapp.id}"
  port              = 8080
  protocol          = "HTTP"

  default_action {
    target_group_arn = "${aws_alb_target_group.webapp.id}"
    type             = "forward"
  }
}

resource "aws_alb" "bitcoind" {
  count = 1
  name  = "${var.project_name}-${terraform.workspace}-bitcoind"

  subnets = [
    "${aws_subnet.main.*.id}",
  ]

  internal = true

  security_groups = [
    "${aws_security_group.alb.id}",
  ]
}

resource "aws_alb_target_group" "bitcoind" {
  count = 1

  depends_on = [
    "aws_alb.bitcoind",
  ]

  name                 = "${var.project_name}-${terraform.workspace}-bitcoind"
  port                 = 8332
  protocol             = "HTTP"
  vpc_id               = "${aws_vpc.main.id}"
  deregistration_delay = 5

  health_check {
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 10
    matcher             = "405"
    path                = "/"
  }
}

resource "aws_alb_listener" "bitcoind" {
  count = 1

  load_balancer_arn = "${aws_alb.bitcoind.id}"
  port              = 8332
  protocol          = "HTTP"

  default_action {
    target_group_arn = "${aws_alb_target_group.bitcoind.id}"
    type             = "forward"
  }
}

resource "aws_alb" "geth" {
  count = 1
  name  = "${var.project_name}-${terraform.workspace}-geth"

  subnets = [
    "${aws_subnet.main.*.id}",
  ]

  internal = true

  security_groups = [
    "${aws_security_group.alb.id}",
  ]
}

resource "aws_alb_target_group" "geth" {
  count = 1

  depends_on = [
    "aws_alb.geth",
  ]

  name                 = "${var.project_name}-${terraform.workspace}-geth"
  port                 = 8545
  protocol             = "HTTP"
  vpc_id               = "${aws_vpc.main.id}"
  deregistration_delay = 5

  health_check {
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 10
    matcher             = "200"
    path                = "/"
  }
}

resource "aws_alb_listener" "geth" {
  count = 1

  load_balancer_arn = "${aws_alb.geth.id}"
  port              = 8545
  protocol          = "HTTP"

  default_action {
    target_group_arn = "${aws_alb_target_group.geth.id}"
    type             = "forward"
  }
}

resource "aws_alb" "btc-signer" {
  count = 1
  name  = "${var.project_name}-${terraform.workspace}-btc-signer"

  subnets = [
    "${aws_subnet.main.*.id}",
  ]

  internal = true

  security_groups = [
    "${aws_security_group.alb.id}",
  ]
}

resource "aws_alb_target_group" "btc-signer" {
  count = 1

  depends_on = [
    "aws_alb.btc-signer",
  ]

  name                 = "${var.project_name}-${terraform.workspace}-btc-signer"
  port                 = 9000
  protocol             = "HTTP"
  vpc_id               = "${aws_vpc.main.id}"
  deregistration_delay = 5

  health_check {
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 10
    matcher             = "404"
    path                = "/"
  }
}

resource "aws_alb_listener" "btc-signer" {
  count = 1

  load_balancer_arn = "${aws_alb.btc-signer.id}"
  port              = 9000
  protocol          = "HTTP"

  default_action {
    target_group_arn = "${aws_alb_target_group.btc-signer.id}"
    type             = "forward"
  }
}

resource "aws_alb" "eth-signer" {
  count = 1
  name  = "${var.project_name}-${terraform.workspace}-eth-signer"

  subnets = [
    "${aws_subnet.main.*.id}",
  ]

  internal = true

  security_groups = [
    "${aws_security_group.alb.id}",
  ]
}

resource "aws_alb_target_group" "eth-signer" {
  count = 1

  depends_on = [
    "aws_alb.eth-signer",
  ]

  name                 = "${var.project_name}-${terraform.workspace}-eth-signer"
  port                 = 9001
  protocol             = "HTTP"
  vpc_id               = "${aws_vpc.main.id}"
  deregistration_delay = 5

  health_check {
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 10
    matcher             = "404"
    path                = "/"
  }
}

resource "aws_alb_listener" "eth-signer" {
  count = 1

  load_balancer_arn = "${aws_alb.eth-signer.id}"
  port              = 9001
  protocol          = "HTTP"

  default_action {
    target_group_arn = "${aws_alb_target_group.eth-signer.id}"
    type             = "forward"
  }
}
