resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags {
    Name = "${var.project_name}-${terraform.workspace}"
    Env  = "${terraform.workspace}"
  }
}

resource "aws_subnet" "main" {
  cidr_block        = "${cidrsubnet(aws_vpc.main.cidr_block, 8, count.index + 1)}"
  vpc_id            = "${aws_vpc.main.id}"
  availability_zone = "${var.aws_region}${element(split(",", var.aws_zones), count.index)}"
  count             = "${length(split(",", var.aws_zones))}"

  tags {
    Name = "${var.project_name}-${terraform.workspace}-${count.index}"
    Env  = "${terraform.workspace}"
  }
}

resource "aws_internet_gateway" "main" {
  vpc_id = "${aws_vpc.main.id}"

  tags = {
    Name = "${var.project_name}-${terraform.workspace}"
    Env  = "${terraform.workspace}"
  }
}

resource "aws_route_table" "routes" {
  vpc_id = "${aws_vpc.main.id}"

  tags = {
    Name = "${var.project_name}-${terraform.workspace}"
    Env  = "${terraform.workspace}"
  }
}

resource "aws_route" "internet" {
  route_table_id         = "${aws_route_table.routes.id}"
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = "${aws_internet_gateway.main.id}"
}

resource "aws_route_table_association" "public" {
  count          = "${length(split(",", var.aws_zones))}"
  subnet_id      = "${element(aws_subnet.main.*.id, count.index)}"
  route_table_id = "${aws_route_table.routes.id}"
}
