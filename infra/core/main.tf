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
  neo4j_instance_type                           = var.neo4j_instance_type
  neo4j_key_pair_name                           = var.neo4j_key_pair_name
  neo4j_resource_prefix                         = var.neo4j_resource_prefix
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

  bastion_host_key_pair_name        = var.bastion_host_key_pair_name
  home_ip                           = "${var.home_ip}/32"
  
  tags = {
    Application = local.app_name
    Blueprint   = local.app_name
    Environment = local.environment
    GithubRepo  = local.repo
    Region      = local.aws_region
  }

  # **********************************************************
  # * SERVICES CONFIGURATION                                 *
  # **********************************************************
  arxiv_base_url            = var.arxiv_base_url
  arxiv_summary_set         = var.arxiv_summary_set
  basic_execution_role_arn  = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  default_lambda_runtime    = var.default_lambda_runtime
  lambda_vpc_access_role    = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
  neo4j_password            = var.neo4j_password
  neo4j_uri                 = "neo4j://${module.data_management.neo4j_instance_private_ip}:7687"
  neo4j_username            = var.neo4j_username

  services_layer_service_name                             = var.services_layer_service_name
  services_layer_service_version                          = var.services_layer_service_version

  fetch_daily_summaries_max_retries                       = var.fetch_daily_summaries_max_retries
  fetch_daily_summaries_service_name                      = var.fetch_daily_summaries_service_name
  fetch_daily_summaries_service_version                   = var.fetch_daily_summaries_service_version

  parse_arxiv_summaries_service_name                      = var.parse_arxiv_summaries_service_name
  parse_arxiv_summaries_service_version                   = var.parse_arxiv_summaries_service_version

  post_arxiv_parse_dispatcher_service_name                = var.post_arxiv_parse_dispatcher_service_name
  post_parse_arxiv_summaries_dispatcher_service_version   = var.post_arxiv_parse_dispatcher_service_version

  store_arxiv_summaries_service_name                      = var.store_arxiv_summaries_service_name
  store_arxiv_summaries_service_version                   = var.store_arxiv_summaries_service_version

  persist_arxiv_summaries_service_name                    = var.persist_arxiv_summaries_service_name
  persist_arxiv_summaries_service_version                 = var.persist_arxiv_summaries_service_version
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

module "services_layer" {
  source = "./services/services_layer"

  app_name        = local.app_name
  aws_region      = local.aws_region
  environment     = local.environment
  runtime         = local.default_lambda_runtime
  service_name    = local.services_layer_service_name
  service_version = local.services_layer_service_version
}

module "fetch_daily_summaries" {
  source = "./services/fetch_daily_summaries"

  app_name                  = local.app_name
  arxiv_base_url            = local.arxiv_base_url
  arxiv_summary_set         = local.arxiv_summary_set
  aws_region                = local.aws_region
  aws_vpc_id                = module.networking.main_vpc_id
  basic_execution_role_arn  = local.basic_execution_role_arn
  data_bucket               = module.data_management.aws_s3_bucket_atomiklabs_data_bucket
  data_bucket_arn           = module.data_management.aws_s3_bucket_atomiklabs_data_bucket_arn
  data_ingestion_key_prefix = local.data_ingestion_key_prefix
  environment               = local.environment
  infra_config_bucket       = local.infra_config_bucket
  lambda_vpc_access_role    = local.lambda_vpc_access_role
  services_layer_arn        = module.services_layer.services_layer_arn
  max_retries               = local.fetch_daily_summaries_max_retries
  neo4j_password            = local.neo4j_password
  neo4j_uri                 = local.neo4j_uri
  neo4j_username            = local.neo4j_username
  private_subnets           = module.networking.aws_private_subnet_ids
  runtime                   = local.default_lambda_runtime
  service_name              = local.fetch_daily_summaries_service_name
  service_version           = local.fetch_daily_summaries_service_version
}

module "parse_arxiv_summaries" {
  source = "./services/parse_arxiv_summaries"

  app_name                  = local.app_name
  aws_region                = local.aws_region
  aws_vpc_id                = module.networking.main_vpc_id
  basic_execution_role_arn  = local.basic_execution_role_arn
  data_bucket               = module.data_management.aws_s3_bucket_atomiklabs_data_bucket
  data_bucket_arn           = module.data_management.aws_s3_bucket_atomiklabs_data_bucket_arn
  data_ingestion_key_prefix = local.data_ingestion_key_prefix
  environment               = local.environment
  etl_key_prefix            = local.etl_key_prefix
  lambda_vpc_access_role    = local.lambda_vpc_access_role
  services_layer_arn        = module.services_layer.services_layer_arn
  neo4j_password            = local.neo4j_password
  neo4j_uri                 = local.neo4j_uri
  neo4j_username            = local.neo4j_username
  private_subnets           = module.networking.aws_private_subnet_ids
  runtime                   = local.default_lambda_runtime
  service_name              = local.parse_arxiv_summaries_service_name
  service_version           = local.parse_arxiv_summaries_service_version
}

module "store_arxiv_summaries" {
  source = "./services/store_arxiv_summaries"
  
  app_name                  = local.app_name
  aws_region                = local.aws_region
  aws_vpc_id                = module.networking.main_vpc_id
  basic_execution_role_arn  = local.basic_execution_role_arn
  data_bucket               = module.data_management.aws_s3_bucket_atomiklabs_data_bucket
  data_bucket_arn           = module.data_management.aws_s3_bucket_atomiklabs_data_bucket_arn
  environment               = local.environment
  etl_key_prefix            = local.etl_key_prefix
  lambda_vpc_access_role    = local.lambda_vpc_access_role
  services_layer_arn        = module.services_layer.services_layer_arn
  neo4j_password            = local.neo4j_password
  neo4j_uri                 = local.neo4j_uri
  neo4j_username            = local.neo4j_username
  private_subnets           = module.networking.aws_private_subnet_ids
  records_prefix            = local.records_prefix
  runtime                   = local.default_lambda_runtime
  service_name              = local.store_arxiv_summaries_service_name
  service_version           = local.store_arxiv_summaries_service_version
}

module "persist_arxiv_summaries" {
  source = "./services/persist_arxiv_summaries"

  app_name                  = local.app_name
  aws_region                = local.aws_region
  aws_vpc_id                = module.networking.main_vpc_id
  basic_execution_role_arn  = local.basic_execution_role_arn
  data_bucket               = module.data_management.aws_s3_bucket_atomiklabs_data_bucket
  data_bucket_arn           = module.data_management.aws_s3_bucket_atomiklabs_data_bucket_arn
  environment               = local.environment
  etl_key_prefix            = local.etl_key_prefix
  lambda_vpc_access_role    = local.lambda_vpc_access_role
  services_layer_arn        = module.services_layer.services_layer_arn
  private_subnets           = module.networking.aws_private_subnet_ids
  records_prefix            = local.records_prefix
  runtime                   = local.default_lambda_runtime
  service_name              = local.persist_arxiv_summaries_service_name
  service_version           = local.persist_arxiv_summaries_service_version
}

module "post_arxiv_parse_dispatcher" {
  source = "./services/post_arxiv_parse_dispatcher"

  app_name                  = local.app_name
  aws_region                = local.aws_region
  aws_vpc_id                = module.networking.main_vpc_id
  basic_execution_role_arn  = local.basic_execution_role_arn
  dispatch_lambda_names     = [ 
                                module.store_arxiv_summaries.store_arxiv_summaries_name,
                                module.persist_arxiv_summaries.persist_arxiv_summaries_name,
                              ]
  environment               = local.environment
  lambda_vpc_access_role    = local.lambda_vpc_access_role
  services_layer_arn        = module.services_layer.services_layer_arn
  private_subnets           = module.networking.aws_private_subnet_ids
  runtime                   = local.default_lambda_runtime
  service_name              = local.post_arxiv_parse_dispatcher_service_name
  service_version           = local.post_parse_arxiv_summaries_dispatcher_service_version
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
                                                      module.fetch_daily_summaries.fetch_daily_summaries_security_group_id,
                                                      module.parse_arxiv_summaries.parse_arxiv_summaries_security_group_id,
                                                      module.store_arxiv_summaries.store_arxiv_summaries_security_group_id
                                                    ]
  private_subnets                                 = module.networking.aws_private_subnet_ids
  region                                          = local.aws_region
  ssm_policy_for_instances_arn                    = local.ssm_policy_for_instances_arn
  tags                                            = local.tags
}

module "events" {
  source = "./events"

  data_bucket                       = module.data_management.aws_s3_bucket_atomiklabs_data_bucket
  data_bucket_arn                   = module.data_management.aws_s3_bucket_atomiklabs_data_bucket_arn
  data_ingestion_key_prefix         = local.data_ingestion_key_prefix
  environment                       = local.environment
  etl_key_prefix                    = local.etl_key_prefix
  parse_arxiv_summaries_name        = module.parse_arxiv_summaries.lambda_name
  parse_arxiv_summaries_arn         = module.parse_arxiv_summaries.lambda_arn
  post_arxiv_parse_dispatcher_name  = module.post_arxiv_parse_dispatcher.lambda_name
  post_arxiv_parse_dispatcher_arn   = module.post_arxiv_parse_dispatcher.lambda_arn
}

