resource "aws_vpc" "atomiklabs_vpc" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name = "${var.environment}-vpc"
  }
}

resource "aws_subnet" "public_subnet" {
  count = length(var.public_subnet_cidrs)

  vpc_id            = aws_vpc.atomiklabs_vpc.id
  cidr_block        = var.public_subnet_cidrs[count.index]
  availability_zone = element(var.availability_zones, count.index)
  map_public_ip_on_launch = true
  tags = {
    Name = "${var.environment}-public-subnet-${count.index + 1}"
  }
}

resource "aws_subnet" "private_subnet" {
  count = length(var.private_subnet_cidrs)

  vpc_id            = aws_vpc.atomiklabs_vpc.id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = element(var.availability_zones, count.index)
  map_public_ip_on_launch = false
  tags = {
    Name = "${var.environment}-private-subnet-${count.index + 1}"
  }
}

resource "aws_eip" "nat" {
  domain = "vpc"
  tags = {
    Name = "${var.environment}-nat-eip"
  }
}

resource "aws_nat_gateway" "nat" {
  allocation_id = aws_eip.nat.id
  subnet_id     = element(aws_subnet.public_subnet.*.id, 0)
  tags = {
    Name = "${var.environment}-nat-gateway"
  }
}

resource "aws_internet_gateway" "atomiklabs_igw" {
  vpc_id = aws_vpc.atomiklabs_vpc.id
  tags = {
    Name = "${var.environment}-igw"
  }
}

resource "aws_route_table" "public_route_table" {
  vpc_id = aws_vpc.atomiklabs_vpc.id
  tags = {
    Name = "${var.environment}-public-route-table"
  }
}

resource "aws_route" "internet_access" {
  route_table_id         = aws_route_table.public_route_table.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.atomiklabs_igw.id
}

resource "aws_route_table_association" "public_subnet_association" {
  count = length(var.public_subnet_cidrs)

  subnet_id      = element(aws_subnet.public_subnet.*.id, count.index)
  route_table_id = aws_route_table.public_route_table.id
}

resource "aws_route_table" "private_route_table" {
  vpc_id = aws_vpc.atomiklabs_vpc.id
  tags = {
    Name = "${var.environment}-private-route-table"
  }
}

resource "aws_route" "private_internet_access" {
  route_table_id         = aws_route_table.private_route_table.id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.nat.id
}

resource "aws_route_table_association" "private_subnet_association" {
  count = length(var.private_subnet_cidrs)

  subnet_id      = element(aws_subnet.private_subnet.*.id, count.index)
  route_table_id = aws_route_table.private_route_table.id
}