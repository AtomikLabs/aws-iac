terraform {
  backend "s3" {
    bucket         = "atomiklabs-infra-config-bucket"
    key            = "terraform/terraform.state"
    region         = "us-east-1"
    dynamodb_table = "atomiklabs-terraform-locks"
    encrypt        = true
  }
}

locals {
  # AWS CONFIGURATION
  account_id = data.aws_caller_identity.current.account_id
  partition  = data.aws_partition.current.partition
  
  # INFRASTRUCTURE CONFIGURATION
  aws_region                      = var.aws_region
  backend_dynamodb_table          = var.backend_dynamodb_table
  environment                     = var.environment
  iam_user_name                   = var.iam_user_name
  infra_config_bucket             = var.infra_config_bucket
  infra_config_prefix             = var.infra_config_prefix
  name                            = var.name
  outputs_prefix                  = var.outputs_prefix
  repo                            = var.repo
  
  # DATA INGESTION CONFIGURATION
  arxiv_base_url                          = var.arxiv_base_url
  arxiv_summary_set                       = var.arxiv_summary_set
  fetch_daily_summaries_name              = var.fetch_daily_summaries_name
  fetch_daily_summaries_version           = var.fetch_daily_summaries_version
  max_daily_summary_fetch_attempts        = 10

  # METADATA CONFIGURATION
  data_ingestion_metadata_key_prefix = var.data_ingestion_metadata_key_prefix
  tags = {
    Blueprint   = local.name
    GithubRepo  = local.repo
    Environment = local.environment
    Region      = local.aws_region
    Application = local.name
  }
}

data "aws_availability_zones" "available" {}
data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}