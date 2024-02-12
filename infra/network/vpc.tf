resource "aws_vpc" "atomiklabs_vpc" {
  cidr_block           = var.VPC_CIDR
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name = "${var.ENVIRONMENT_NAME}-vpc"
  }
}

resource "aws_subnet" "public_subnet" {
  count = length(var.SUBNET_CIDRS.public)

  vpc_id            = aws_vpc.atomiklabs_vpc.id
  cidr_block        = var.SUBNET_CIDRS.public[count.index]
  availability_zone = element(var.AVAILABILITY_ZONES, count.index)
  map_public_ip_on_launch = true
  tags = {
    Name = "${var.ENVIRONMENT_NAME}-public-subnet-${count.index + 1}"
  }
}

resource "aws_internet_gateway" "atomiklabs_igw" {
  vpc_id = aws_vpc.atomiklabs_vpc.id
  tags = {
    Name = "${var.ENVIRONMENT_NAME}-igw"
  }
}

resource "aws_route_table" "public_route_table" {
  vpc_id = aws_vpc.atomiklabs_vpc.id
  tags = {
    Name = "${var.ENVIRONMENT_NAME}-public-route-table"
  }
}

resource "aws_route" "internet_access" {
  route_table_id         = aws_route_table.public_route_table.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.atomiklabs_igw.id
}

resource "aws_route_table_association" "public_subnet_association" {
  count = length(var.SUBNET_CIDRS.PUBLIC)

  subnet_id      = element(aws_subnet.public_subnet.*.id, count.index)
  route_table_id = aws_route_table.public_route_table.id
}
