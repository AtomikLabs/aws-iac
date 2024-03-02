# **********************************************************
# * NETWORKING                                             *
# **********************************************************

output "main_vpc_id" {
  value = module.networking.aws_vpc.main.id
}

output "aws_public_subnet_ids" {
  value = module.networking.aws_subnet.public[*].id
}

output "aws_private_subnet_ids" {
  value = module.networking.aws_subnet.private[*].id
}
