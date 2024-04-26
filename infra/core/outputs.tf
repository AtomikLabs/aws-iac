
# **********************************************************
# DATA MANAGEMENT                                          *
# **********************************************************
output "aws_iam_policy_s3_infra_config_bucket_access" {
    description = "IAM policy for S3 infra config bucket access"
    value       = module.data_management.aws_iam_policy_s3_infra_config_bucket_access
}

output "data_bucket" {
  description = "S3 bucket for atomiklabs data"
  value       = module.data_management.aws_s3_bucket_atomiklabs_data_bucket
}

output "data_bucket_arn" {
  description = "S3 bucket ARN for atomiklabs data"
  value       = module.data_management.aws_s3_bucket_atomiklabs_data_bucket_arn
}

output "neo4j_instance_private_ip" {
  description = "Private IP of Neo4j instance"
  value       = module.data_management.neo4j_instance_private_ip
}

# **********************************************************
# * ORCHESTRATION                                          *
# **********************************************************

output "orchestration_instance_id" {
  description = "ID of the orchestration instance"
  value       = module.orchestration.airflow_instance_id
}

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
