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
  # * Data Management                                        *
  # **********************************************************
  data_ingestion_metadata_key_prefix            = var.data_ingestion_metadata_key_prefix
  neo4j_ami_id                                  = var.neo4j_ami_id
  neo4j_instance_type                           = var.neo4j_instance_type
  neo4j_key_pair_name                           = var.neo4j_key_pair_name
  neo4j_resource_prefix                         = var.neo4j_resource_prefix
  
  # **********************************************************
  # * INFRASTRUCTURE CONFIGURATION                           *
  # **********************************************************
  alert_email                     = var.alert_email
  backend_dynamodb_table          = var.backend_dynamodb_table
  default_ami_id                  = var.default_ami_id
  environment                     = var.environment
  infra_config_bucket             = var.infra_config_bucket
  infra_config_bucket_arn         = var.infra_config_bucket_arn
  infra_config_prefix             = var.infra_config_prefix
  name                            = var.name
  repo                            = var.repo
  ssm_policy_for_instances_arn    = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
  terraform_outputs_prefix        = var.terraform_outputs_prefix
  
  # **********************************************************
  # * NETWORKING CONFIGURATION                               *
  # **********************************************************

  bastion_host_key_pair_name        = var.bastion_host_key_pair_name
  home_ip                           = "${var.home_ip}/32"
  
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

 module "security" {
  source = "./security"

  aws_ssm_managed_instance_core_arn = local.ssm_policy_for_instances_arn
  bastion_host_key_pair_name        = local.bastion_host_key_pair_name
  environment                       = local.environment
  home_ip                           = local.home_ip
  public_subnets                    = module.networking.aws_public_subnet_ids
  vpc_id                            = module.networking.main_vpc_id
 }

module "data_management" {
  source = "./data_management"

  availability_zones                            = data.aws_availability_zones.available.names
  aws_vpc_id                                    = module.networking.main_vpc_id
  bastion_host_ip                               = module.security.bastion_host_public_ip
  data_ingestion_metadata_key_prefix            = local.data_ingestion_metadata_key_prefix
  default_ami_id                                = local.default_ami_id
  environment                                   = local.environment
  home_ip                                       = local.home_ip
  infra_config_bucket_arn                       = local.infra_config_bucket_arn
  name                                          = local.name
  neo4j_ami_id                                  = local.neo4j_ami_id
  neo4j_instance_type                           = local.neo4j_instance_type
  neo4j_key_pair_name                           = local.neo4j_key_pair_name
  neo4j_resource_prefix                         = local.neo4j_resource_prefix
  private_subnets                               = module.networking.aws_private_subnet_ids
  region                                        = local.aws_region
  ssm_policy_for_instances_arn                  = local.ssm_policy_for_instances_arn 
  tags                                          = local.tags
}

module "containerization" {
  source = "./containerization"

  environment = local.environment
}