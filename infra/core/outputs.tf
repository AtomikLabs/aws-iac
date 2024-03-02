# **********************************************************
# * NETWORKING                                             *
# **********************************************************

output "main_vpc_id" {
  value = module.networking.main_vpc_id
}

output "aws_private_subnet_ids" {
  value = module.networking.aws_private_subnet_ids
}

output "aws_public_subnet_ids" {
  value = module.networking.aws_public_subnet_ids
}
