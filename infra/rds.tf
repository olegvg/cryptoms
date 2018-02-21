resource "aws_db_subnet_group" "main" {
  name        = "${var.project_name}-${terraform.workspace}"
  description = "${var.project_name}-${terraform.workspace}"

  subnet_ids = [
    "${aws_subnet.main.*.id}",
  ]

  tags {
    Name = "${var.project_name}-${terraform.workspace}"
    Env  = "${terraform.workspace}"
  }
}

resource "aws_db_instance" "db" {
  identifier           = "${var.project_name}-${terraform.workspace}"
  allocated_storage    = "5"
  engine               = "postgres"
  engine_version       = "9.6.5"
  instance_class       = "db.m4.large"
  multi_az             = "false"
  apply_immediately    = true
  name                 = "cryptopayments"
  username             = "cryptopayments"
  password             = "${var.postgres_password}"
  db_subnet_group_name = "${aws_db_subnet_group.main.id}"

  vpc_security_group_ids = [
    "${aws_security_group.postgres.id}",
  ]

  allow_major_version_upgrade = true
  skip_final_snapshot         = true
  publicly_accessible         = true

  tags {
    Name = "${var.project_name}-${terraform.workspace}"
    Env  = "${terraform.workspace}"
  }
}
