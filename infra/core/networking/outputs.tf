output "igw_id" {
  value = aws_internet_gateway.atomiklabs_igw.id
}

output "nat_gateway_id" {
  value = aws_nat_gateway.nat.id
}

output "private_route_table_id" {
  value = aws_route_table.private_route_table.id
}

output "private_subnet_ids" {
  value = aws_subnet.private_subnet[*].id
}

output "public_route_table_id" {
  value = aws_route_table.public_route_table.id
}

output "public_subnet_ids" {
  value = aws_subnet.public_subnet[*].id
}

output "vpc_id" {
  value = aws_vpc.atomiklabs_vpc.id
}
