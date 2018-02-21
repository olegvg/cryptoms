resource "aws_route53_zone" "internal" {
  name    = "${var.project_name}-${terraform.workspace}"
  comment = "${var.project_name}-${terraform.workspace}"
  vpc_id  = "${aws_vpc.main.id}"

  tags {
    Name = "${var.project_name}"
    Env  = "${terraform.workspace}"
  }
}

resource "aws_route53_record" "postgres" {
  zone_id = "${aws_route53_zone.internal.id}"
  name    = "postgres"
  type    = "CNAME"
  ttl     = 60

  records = [
    "${aws_db_instance.db.address}",
  ]
}

resource "aws_route53_record" "bitcoind" {
  zone_id = "${aws_route53_zone.internal.id}"
  name    = "bitcoind"
  type    = "CNAME"
  ttl     = 60

  records = [
    "${aws_alb.bitcoind.dns_name}",
  ]
}

resource "aws_route53_record" "geth" {
  zone_id = "${aws_route53_zone.internal.id}"
  name    = "geth"
  type    = "CNAME"
  ttl     = 60

  records = [
    "${aws_alb.geth.dns_name}",
  ]
}

resource "aws_route53_record" "btc-signer" {
  zone_id = "${aws_route53_zone.internal.id}"
  name    = "btc-signer"
  type    = "CNAME"
  ttl     = 60

  records = [
    "${aws_alb.btc-signer.dns_name}",
  ]
}

resource "aws_route53_record" "eth-signer" {
  zone_id = "${aws_route53_zone.internal.id}"
  name    = "eth-signer"
  type    = "CNAME"
  ttl     = 60

  records = [
    "${aws_alb.eth-signer.dns_name}",
  ]
}

data "aws_route53_zone" "cryptopayments_cryptology_com" {
  name = "cryptopayments.cryptology.com."
}

resource "aws_route53_record" "webapp-domain" {
  count = 1

  zone_id = "${data.aws_route53_zone.cryptopayments_cryptology_com.id}"
  name    = "${var.webapp_domain}"
  type    = "A"

  alias {
    name                   = "${aws_alb.webapp.dns_name}"
    zone_id                = "${aws_alb.webapp.zone_id}"
    evaluate_target_health = false
  }
}
