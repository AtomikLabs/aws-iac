# **********************************************************
# * Core Config                                            *
# **********************************************************

variable "alert_email"  {
  description = "Email to receive alerts"
  type        = string
}

variable "app_name" {
  description = "Base name of the application"
  type        = string
  default     = "atomiklabs"
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

variable "default_ami_id" {
  description = "Default AMI ID"
  type        = string
}

variable "environment" {
  description = "Environment"
  type        = string
  default     = "dev"
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
    description = "Prefix for the ETL keys"
    type        = string
}

variable "neo4j_ami_id" {
  description = "Neo4j AMI ID"
  type        = string
}

variable "neo4j_instance_type" {
  description = "Neo4j instance type"
  type        = string
}

variable "neo4j_key_pair_name" {
  description = "Neo4j key pair name"
  type        = string
}

variable "neo4j_host_username" {
  description = "Neo4j host username"
  type        = string
}

variable "neo4j_password" {
  description = "Neo4j password"
  type        = string
}

variable "neo4j_resource_prefix" {
  description = "Prefix for the resources"
  type        = string
}

variable "neo4j_username" {
  description = "Neo4j username"
  type        = string
}

variable "records_prefix" {
  description = "Prefix for the records"
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
# * Orchestration                                          *
# **********************************************************

variable "orchestration_ami_id" {
  description = "Orchestration AMI ID"
  type        = string
}

variable "orchestration_instance_type" {
  description = "Orchestration instance type"
  type        = string
}

variable "orchestration_key_pair_name" {
  description = "Orchestration key pair name"
  type        = string
}

variable "orchestration_resource_prefix" {
  description = "Prefix for the orchestration resources"
  type        = string
}

variable "orchestration_username" {
  description = "Orchestration username"
  type        = string
}

# **********************************************************
# * Security                                               *
# **********************************************************

variable "bastion_ami_id" {
  description = "Bastion AMI ID"
  type        = string
}

variable "bastion_host_key_pair_name" {
  description = "Bastion host key pair name"
  type        = string
}

variable "bastion_instance_type" {
  description = "Bastion instance type"
  type        = string
}

variable "bastion_host_username" {
  description = "Bastion host username"
  type        = string
}

# **********************************************************
# * Services                                               *
# **********************************************************

variable "arxiv_api_max_retries" {
  description = "Max retries for fetches from the arXiv API"
  type        = number
}

variable "arxiv_base_url" {
  description = "Base URL for the Arxiv API"
  type        = string
}

variable "arxiv_sets" {
  description = "Arxiv sets"
  type        = list(string)
}
