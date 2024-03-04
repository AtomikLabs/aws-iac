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

variable "infra_config_bucket_arn" {
  description = "S3 bucket ARN to store the infra config"
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

variable "repo" {
  description = "application Github repository"
  type        = string
}

variable "terraform_outputs_prefix" {
  description = "Prefix for the Terraform outputs"
  type        = string
}

# **********************************************************
# * Data Management                                        *
# **********************************************************

variable "data_ingestion_key_prefix" {
    description = "Prefix for the data ingestion"
    type        = string
}

variable "data_ingestion_metadata_key_prefix" {
    description = "Prefix for the data ingestion metadata"
    type        = string
}

variable "etl_key_prefix" {
    description = "Prefix for the ETL"
    type        = string
}

# **********************************************************
# * Messaging                                              *
# **********************************************************
variable "rabbitmqctl_username" {
  description = "RabbitMQ control username"
  type        = string
}

variable "rabbitmqctl_password" {
  description = "RabbitMQ control password"
  type        = string
}

# **********************************************************
# * Networking                                             *
# **********************************************************

variable "home_ip" {
  description = "Home IP"
  type        = string
}

# **********************************************************
# * Observability                                          *
# **********************************************************

variable "bastion_host_key_pair_name" {
  description = "Bastion host key pair name"
  type        = string
}

# **********************************************************
# * Services                                               *
# **********************************************************

variable "arxiv_base_url" {
  description = "ArXiv base URL"
  type        = string
}

variable "arxiv_summary_set" {
  description = "ArXiv summary set to fetch"
  type        = string
}

variable "fetch_daily_summaries_name" {
  description = "Name of the fetch daily summaries function"
  type        = string
}

variable "fetch_daily_summaries_version" {
  description = "Version of the fetch daily summaries function"
  type        = string
}