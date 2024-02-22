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
  # **********************************************************
  # * AWS ACCOUNT                                            *
  # **********************************************************
  account_id                = data.aws_caller_identity.current.account_id
  aws_region                = var.aws_region
  partition                 = data.aws_partition.current.partition
  
  # **********************************************************
  # * INFRASTRUCTURE CONFIGURATION                           *
  # **********************************************************
  alert_email                     = var.alert_email
  backend_dynamodb_table          = var.backend_dynamodb_table
  environment                     = var.environment
  iam_user_name                   = var.iam_user_name
  infra_config_bucket             = var.infra_config_bucket
  infra_config_prefix             = var.infra_config_prefix
  name                            = var.name
  outputs_prefix                  = var.outputs_prefix
  repo                            = var.repo
  
  # **********************************************************
  # * SERVICES CONFIGURATION                                 *
  # **********************************************************
  AWSBasicExecutionRoleARN        = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  
  # **********************************************************
  # * DATA INGESTION CONFIGURATION                           *
  # **********************************************************
  arxiv_base_url                          = var.arxiv_base_url
  arxiv_summary_set                       = var.arxiv_summary_set
  data_ingestion_key_prefix               = var.data_ingestion_key_prefix
  fetch_daily_summaries_name              = var.fetch_daily_summaries_name
  fetch_daily_summaries_version           = var.fetch_daily_summaries_version
  max_daily_summary_fetch_attempts        = 10

  # **********************************************************
  # * ETL CONFIGURATION                                      *
  # **********************************************************

  etl_key_prefix                    = var.etl_key_prefix
  AWSGlueServiceRoleARN             = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"

  # **********************************************************
  # * METADATA CONFIGURATION                                 *
  # **********************************************************
  data_ingestion_metadata_key_prefix = var.data_ingestion_metadata_key_prefix

  # **********************************************************
  # * NETWORKING CONFIGURATION                               *
  # **********************************************************

  availability_zones               = var.availability_zones
  bastion_host_key_pair_name       = var.bastion_host_key_pair_name
  home_ip                          = "${var.home_ip}/32"
  vpc_cidr                         = "10.0.0.0/16"
  public_subnet_cidrs              = ["10.0.1.0/24", "10.0.2.0/24"]
  private_subnet_cidrs             = ["10.0.3.0/24", "10.0.4.0/24"]
  tags = {
    Blueprint   = local.name
    GithubRepo  = local.repo
    Environment = local.environment
    Region      = local.aws_region
    Application = local.name
  }
}

module "data_management" {
  source                              = "./data_management"
  app_name                            = local.name
  aws_region                          = local.aws_region
  data_ingestion_metadata_key_prefix  = local.data_ingestion_metadata_key_prefix
  environment                         = local.environment
  tags                                = local.tags
}

module "networking" {
  source                = "./networking"
  app_name              = local.name
  availability_zones    = local.availability_zones
  aws_region            = local.aws_region
  environment           = local.environment
  private_subnet_cidrs  = local.private_subnet_cidrs
  public_subnet_cidrs   = local.public_subnet_cidrs
  tags                  = local.tags
  vpc_cidr              = local.vpc_cidr
}