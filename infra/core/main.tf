terraform {
  backend "s3" {
    bucket         = "atomiklabs-infra-config-bucket"
    dynamodb_table = "atomiklabs-terraform-locks"
    encrypt        = true
    key            = "terraform/terraform.state"
    region         = "us-east-1"
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
  infra_config_bucket_arn         = var.infra_config_bucket_arn
  infra_config_prefix             = var.infra_config_prefix
  name                            = var.name
  repo                            = var.repo
  terraform_outputs_prefix        = var.terraform_outputs_prefix
  
  # **********************************************************
  # * NETWORKING CONFIGURATION                               *
  # **********************************************************

  bastion_host_key_pair_name        = var.bastion_host_key_pair_name
  home_ip                           = "${var.home_ip}/32"

  # **********************************************************
  # * MESSAGING CONFIGURATION                                *
  # **********************************************************
  rabbitmqctl_username              = var.rabbitmqctl_username
  rabbitmqctl_password              = var.rabbitmqctl_password
  
  tags = {
    Application = local.name
    Blueprint   = local.name
    Environment = local.environment
    GithubRepo  = local.repo
    Region      = local.aws_region
  }
}

module "networking" {
  source = "./networking"

  availability_zone_available_names = data.aws_availability_zones.available.names
  environment                       = local.environment
  home_ip                           = var.home_ip
}

module "data_management" {
  source = "./data_management"

  aws_vpc_id                        = module.networking.aws_vpc_id
  data_ingestion_metadata_key_prefix = var.data_ingestion_metadata_key_prefix
  environment                      = local.environment
  home_ip                          = var.home_ip
  infra_config_bucket_arn          = local.infra_config_bucket_arn
  name                             = local.name
  tags                             = local.tags
}