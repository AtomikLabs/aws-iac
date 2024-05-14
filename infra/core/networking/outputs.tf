output "main_vpc_id" {
  value = aws_vpc.main.id
}

output "aws_private_subnet_ids" {
  value = aws_subnet.private[*].id
}

output "aws_public_subnet_ids" {
  value = aws_subnet.public[*].id
}
