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
  data_ingestion_key_prefix                     = var.data_ingestion_key_prefix
  data_ingestion_metadata_key_prefix            = var.data_ingestion_metadata_key_prefix
  etl_key_prefix                                = var.etl_key_prefix
  neo4j_ami_id                                  = var.neo4j_ami_id
  neo4j_host_username                           = var.neo4j_host_username
  neo4j_instance_type                           = var.neo4j_instance_type
  neo4j_key_pair_name                           = var.neo4j_key_pair_name
  neo4j_password                                = var.neo4j_password
  neo4j_resource_prefix                         = var.neo4j_resource_prefix
  neo4j_username                                = var.neo4j_username
  records_prefix                                = var.records_prefix
  
  # **********************************************************
  # * INFRASTRUCTURE CONFIGURATION                           *
  # **********************************************************
  alert_email                     = var.alert_email
  app_name                        = var.app_name
  backend_dynamodb_table          = var.backend_dynamodb_table
  default_ami_id                  = var.default_ami_id
  environment                     = var.environment
  infra_config_bucket             = var.infra_config_bucket
  infra_config_bucket_arn         = var.infra_config_bucket_arn
  infra_config_prefix             = var.infra_config_prefix
  repo                            = var.repo
  ssm_policy_for_instances_arn    = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
  terraform_outputs_prefix        = var.terraform_outputs_prefix
  
  # **********************************************************
  # * NETWORKING CONFIGURATION                               *
  # **********************************************************

  home_ip                           = "${var.home_ip}/32"
  
  tags = {
    Application = local.app_name
    Blueprint   = local.app_name
    Environment = local.environment
    GithubRepo  = local.repo
    Region      = local.aws_region
  }

  # **********************************************************
  # * ORCHESTRATION CONFIGURATION                            *
  # **********************************************************

  orchestration_ami_id            = var.orchestration_ami_id
  orchestration_instance_type     = var.orchestration_instance_type
  orchestration_key_pair_name     = var.orchestration_key_pair_name
  orchestration_resource_prefix   = var.orchestration_resource_prefix

  # **********************************************************
  # * SECURITY   CONFIGURATION                               *
  # **********************************************************

  bastion_ami_id                    = var.bastion_ami_id
  bastion_host_key_pair_name        = var.bastion_host_key_pair_name
  bastion_instance_type             = var.bastion_instance_type
  bastion_host_username             = var.bastion_host_username

  # **********************************************************
  # * SERVICES CONFIGURATION                                 *
  # **********************************************************
  arxiv_api_max_retries     = var.arxiv_api_max_retries
  arxiv_base_url            = var.arxiv_base_url
  arxiv_sets                = var.arxiv_sets
  basic_execution_role_arn  = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  lambda_vpc_access_role    = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
  neo4j_uri                 = "neo4j://${module.data_management.neo4j_instance_private_ip}:7687"
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
  bastion_ami_id                    = local.bastion_ami_id
  bastion_host_key_pair_name        = local.bastion_host_key_pair_name
  bastion_instance_type             = local.bastion_instance_type
  environment                       = local.environment
  home_ip                           = local.home_ip
  public_subnets                    = module.networking.aws_public_subnet_ids
  vpc_id                            = module.networking.main_vpc_id
 }


module "data_management" {
  source = "./data_management"

  app_name                                        = local.app_name
  availability_zones                              = data.aws_availability_zones.available.names
  aws_vpc_id                                      = module.networking.main_vpc_id
  data_ingestion_metadata_key_prefix              = local.data_ingestion_metadata_key_prefix
  default_ami_id                                  = local.default_ami_id
  environment                                     = local.environment
  home_ip                                         = local.home_ip
  infra_config_bucket_arn                         = local.infra_config_bucket_arn
  neo4j_ami_id                                    = local.neo4j_ami_id
  neo4j_instance_type                             = local.neo4j_instance_type
  neo4j_key_pair_name                             = local.neo4j_key_pair_name
  neo4j_resource_prefix                           = local.neo4j_resource_prefix
  neo4j_source_security_group_ids                 = [
                                                      module.security.bastion_host_security_group_id,
                                                      module.orchestration.orchestration_security_group_id,
                                                    ]
  private_subnets                                 = module.networking.aws_private_subnet_ids
  region                                          = local.aws_region
  ssm_policy_for_instances_arn                    = local.ssm_policy_for_instances_arn
  tags                                            = local.tags
}

module "orchestration" {
  source = "./orchestration"

  app_name                                        = local.app_name
  arxiv_api_max_retries                           = local.arxiv_api_max_retries
  arxiv_base_url                                  = local.arxiv_base_url
  arxiv_sets                                      = local.arxiv_sets
  availability_zones                              = data.aws_availability_zones.available.names
  aws_vpc_id                                      = module.networking.main_vpc_id
  data_bucket                                     = module.data_management.aws_s3_bucket_atomiklabs_data_bucket
  data_bucket_arn                                 = module.data_management.aws_s3_bucket_atomiklabs_data_bucket_arn
  default_ami_id                                  = local.default_ami_id
  environment                                     = local.environment
  home_ip                                         = local.home_ip
  infra_config_bucket                             = local.infra_config_bucket
  infra_config_bucket_arn                         = local.infra_config_bucket_arn
  orchestration_ami_id                            = local.orchestration_ami_id
  orchestration_instance_type                     = local.orchestration_instance_type
  orchestration_key_pair_name                     = local.orchestration_key_pair_name
  orchestration_resource_prefix                   = local.orchestration_resource_prefix
  orchestration_source_security_group_ids         = [
                                                      module.security.bastion_host_security_group_id,
                                                    ]
  private_subnets                                 = module.networking.aws_private_subnet_ids
  rabbitmq_source_security_group_ids              = [
                                                      module.networking.neo4j_security_group_id,
                                                      module.security.bastion_host_security_group_id,
                                                    ]
  region                                          = local.aws_region
  ssm_policy_for_instances_arn                    = local.ssm_policy_for_instances_arn
  tags                                            = local.tags
}