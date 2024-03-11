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

variable "data_ingestion_metadata_key_prefix" {
    description = "Prefix for the data ingestion metadata"
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

variable "neo4j_resource_prefix" {
  description = "Prefix for the resources"
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
