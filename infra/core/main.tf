terraform {
  backend "s3" {
    bucket         = "atomiklabs-infra-config-bucket"
    key            = "terraform/terraform.state"
    region         = "us-east-1"
    dynamodb_table = "atomiklabs-terraform-locks"
    encrypt        = true
  }
}

data "aws_availability_zones" "available" {}
data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

locals {
  environment                     = var.environment
  fetch_daily_summaries_image_tag = var.fetch_daily_summaries_image_tag
  iam_user_name                   = var.iam_user_name
  name                            = var.name
  region                          = var.region

  arxiv_base_url = "http://export.arxiv.org/oai2"
  data_ingestion_metadata_key_prefix = "data_ingestion_metadata"
  max_daily_summary_fetch_attempts  = 10
  summary_set                       = "cs"

  account_id = data.aws_caller_identity.current.account_id
  partition  = data.aws_partition.current.partition

  tags = {
    Blueprint   = local.name
    GithubRepo  = "github.com/AtomikLabs/atomiklabs"
    Environment = local.environment
    Region      = local.region
    Application = local.name
  }
}