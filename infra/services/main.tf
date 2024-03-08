terraform {
  backend "s3" {
    bucket         = "atomiklabs-infra-config-bucket"
    key            = "terraform/fetch-daily-summaries.state"
    region         = "us-east-1"
    dynamodb_table = "atomiklabs-fetch-daily-summaries-locks"
    encrypt        = true
  }
}

data "aws_availability_zones" "available" {}
data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

locals {
  # **********************************************************
  # * SERVICES CONFIGURATION                                 *
  # **********************************************************
  AWSBasicExecutionRoleARN                  = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  AWSLambdaVPCAccessExecutionRole           = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
  AmazonSSMManagedInstanceCoreARN           = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
  AmazonSSMManagedEC2InstanceDefaultPolicy  = "arn:aws:iam::aws:policy/AmazonSSMManagedEC2InstanceDefaultPolicy"
  
  # **********************************************************
  # * DATA INGESTION CONFIGURATION                           *
  # **********************************************************
  arxiv_base_url                          = var.arxiv_base_url
  arxiv_summary_set                       = var.arxiv_summary_set
  data_ingestion_key_prefix               = var.data_ingestion_key_prefix
  fetch_daily_summaries_name              = var.service_name
  fetch_daily_summaries_version           = var.service_version
  max_daily_summary_fetch_attempts        = var.fetch_daily_summaries_max_attempts

  # **********************************************************
  # * PROTOTYPE CONFIGURATION                                *
  # **********************************************************

  prototype_name                          = var.prototype_name
  prototype_version                       = var.prototype_version
  max_daily_prototype_attempts            = var.prototype_max_attempts

  # **********************************************************
  # * ETL CONFIGURATION                                      *
  # **********************************************************

  etl_key_prefix                    = var.etl_key_prefix
  AWSGlueServiceRoleARN             = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"

  # **********************************************************
  # * INTEGRATIONS CONFIGURATION                             *
  # **********************************************************

  openai_api_key                  = var.openai_api_key

  
  # **********************************************************
  # * METADATA CONFIGURATION                                 *
  # **********************************************************
  data_ingestion_metadata_key_prefix = var.data_ingestion_metadata_key_prefix

  environment = var.environment
}