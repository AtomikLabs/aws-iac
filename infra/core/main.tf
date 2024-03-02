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
  infra_config_bucket_arn         = var.infra_config_bucket_arn
  infra_config_prefix             = var.infra_config_prefix
  name                            = var.name
  outputs_prefix                  = var.outputs_prefix
  repo                            = var.repo
  
  
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
    Blueprint   = local.name
    GithubRepo  = local.repo
    Environment = local.environment
    Region      = local.aws_region
    Application = local.name
  }
}

module "networking" {
  source = "./networking"

  availability_zone_available_names = data.aws_availability_zones.available.names
  environment                       = local.environment
  home_ip                           = var.home_ip
}
