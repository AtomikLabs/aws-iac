output "aws_internet_gateway_id" {
  value = aws_internet_gateway.gw.id
}

output "main_vpc_id" {
  value = aws_vpc.main.id
}


output "aws_public_route_table_id" {
  value = aws_route_table.public.id
}

output "aws_public_subnet_ids" {
  value = aws_subnet.public[*].id
}




