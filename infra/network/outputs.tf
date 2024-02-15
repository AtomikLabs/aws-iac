output "VPC_ID" {
  value = aws_vpc.atomiklabs_vpc.id
  description = "The ID of the VPC"
}

output "PUBLIC_SUBNET_IDS" {
  value = [for s in aws_subnet.public_subnet : s.id]
  description = "The IDs of the public subnets"
}

output "PRIVATE_SUBNET_IDS" {
  value = [for s in aws_subnet.private_subnet : s.id]
  description = "The IDs of the private subnets"
}

output "SECURITY_GROUP_ID" {
  value = aws_security_group.public_sg.id
  description = "The ID of the security group for public subnets"
}
