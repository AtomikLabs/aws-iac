output "vpc_id" {
  value = aws_vpc.atomiklabs_vpc.id
  description = "The ID of the VPC"
}

output "public_subnet_ids" {
  value = [for s in aws_subnet.public_subnet : s.id]
  description = "The IDs of the public subnets"
}

output "security_group_id" {
  value = aws_security_group.public_sg.id
  description = "The ID of the security group for public subnets"
}
