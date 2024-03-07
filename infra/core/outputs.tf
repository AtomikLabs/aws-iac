# **********************************************************
# * CONTAINERIZATION                                       *
# **********************************************************
output "ecr_repo_url" {
  value = module.containerization.repo_url
}

# **********************************************************
# DATA MANAGEMENT                                          *
# **********************************************************
output "aws_glue_catalog_database_data_catalog_database_arn" {
  description = "AWS Glue Catalog Database ARN for data catalog"
  value       = module.data_management.aws_glue_catalog_database_data_catalog_database_arn
}

output "aws_glue_catalog_database_data_catalog_database_id" {
  description = "AWS Glue Catalog Database ID for data catalog"
  value       = module.data_management.aws_glue_catalog_database_data_catalog_database_id
}

output "aws_glue_catalog_database_data_catalog_database_name" {
  description = "AWS Glue Catalog Database for data catalog"
  value       = module.data_management.aws_glue_catalog_database_data_catalog_database_name
}

output "aws_glue_catalog_table_data_catalog_table_data_ingestion_metadata_table_arn" {
    description = "AWS Glue Catalog Table ARN for data ingestion metadata"
    value       = module.data_management.aws_glue_catalog_table_data_catalog_table_data_ingestion_metadata_table_arn
}

output "aws_glue_catalog_table_data_catalog_table_data_ingestion_metadata_table_id" {
  description = "AWS Glue Catalog Table ID for data ingestion metadata"
  value       = module.data_management.aws_glue_catalog_table_data_catalog_table_data_ingestion_metadata_table_id
}

output "aws_glue_catalog_table_data_catalog_table_data_ingestion_metadata_table_name" {
  description = "AWS Glue Catalog Table for data ingestion metadata"
  value       = module.data_management.aws_glue_catalog_table_data_catalog_table_data_ingestion_metadata_table_name
}

output "aws_iam_policy_s3_infra_config_bucket_access" {
    description = "IAM policy for S3 infra config bucket access"
    value       = module.data_management.aws_iam_policy_s3_infra_config_bucket_access
}

output "data_bucket" {
  description = "S3 bucket for atomiklabs data"
  value       = module.data_management.aws_s3_bucket_atomiklabs_data_bucket.bucket
}

output "data_bucket_arn" {
  description = "S3 bucket ARN for atomiklabs data"
  value       = module.data_management.aws_s3_bucket_atomiklabs_data_bucket.arn
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
