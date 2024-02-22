# **********************************************************
# * Core Config                                            *
# **********************************************************
variable "alert_email"  {
  description = "Email to receive alerts"
  type        = string
}

variable "aws_region" {
  description = "AWS region to deploy the infrastructure"
  type        = string
  default     = "us-east-1"
}

variable "backend_dynamodb_table" {
  description = "DynamoDB table name for Terraform state"
  type        = string
}

variable "environment" {
  description = "Environment"
  type        = string
  default     = "dev"
}

variable "iam_user_name" {
  description = "IAM user name"
  type        = string
  default     = "atomiklabs-dev-ci-cd"
}

variable "infra_config_bucket" {
  description = "S3 bucket to store the infra config"
  type        = string
}

variable "infra_config_prefix" {
  description = "Prefix for the infra config"
  type        = string
}

variable "name" {
  description = "Base name of the application"
  type        = string
  default     = "atomiklabs"
}

variable "outputs_prefix" {
  description = "Prefix for the outputs"
  type        = string
}

variable "repo" {
  description = "application Github repository"
  type        = string
}

# **********************************************************
# * Data Ingestion                                         *
# **********************************************************
variable "arxiv_base_url" {
  description = "arXiv base URL"
  type        = string
}

variable "arxiv_summary_set" {
  description = "arXiv summary set to fetch"
  type        = string
  default     = "cs"
}

variable "data_ingestion_key_prefix" {
  description = "Prefix for the data ingestion"
  type        = string
}

variable "data_ingestion_metadata_key_prefix" {
  description = "Prefix for the data ingestion metadata"
  type        = string
}

variable "fetch_daily_summaries_name" {
  description = "Fetch daily summaries service name"
  type        = string
}

variable "fetch_daily_summaries_version" {
  description = "Fetch daily summaries service version"
  type        = string
}

# **********************************************************
# * ETL                                                    *
# **********************************************************

variable "etl_key_prefix" {
  description = "Prefix for the ETL"
  type        = string
}