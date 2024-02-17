locals {
  # AWS CONFIGURATION
  account_id = data.aws_caller_identity.current.account_id
  partition  = data.aws_partition.current.partition
  
  # INFRASTRUCTURE CONFIGURATION
  aws_region                      = var.aws_region
  backend_dynamodb_table          = var.backend_dynamodb_table
  environment                     = var.environment
  fetch_daily_summaries_image_tag = var.fetch_daily_summaries_image_tag
  iam_user_name                   = var.iam_user_name
  infra_config_bucket             = var.infra_config_bucket
  infra_config_prefix             = var.infra_config_prefix
  name                            = var.name
  outputs_prefix                  = var.outputs_prefix
  repo                            = var.repo
  
  # DATA INGESTION CONFIGURATION
  arxiv_base_url = "http://export.arxiv.org/oai2"
  max_daily_summary_fetch_attempts  = 10
  arxiv_summary_set                       = var.arxiv_summary_set
  arxiv_summary_sets                      = var.arxiv_summary_sets

  # METADATA CONFIGURATION
  data_ingestion_metadata_key_prefix = "data_ingestion_metadata"
  tags = {
    Blueprint   = local.name
    GithubRepo  = local.repo
    Environment = local.environment
    Region      = local.aws_region
    Application = local.name
  }
}

terraform {
  backend "s3" {
    bucket         = var.infra_config_bucket
    key            = var.infra_config_prefix
    aws_region     = var.aws_region
    dynamodb_table = var.backend_dynamodb_table
    encrypt        = true
  }
}

data "aws_availability_zones" "available" {}
data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}