variable "infra_config_bucket_arn" {
  description = "ARN of the infra config bucket"
  type        = string
}

variable "data_ingestion_metadata_key_prefix" {
    description = "Prefix for the data ingestion metadata"
    type        = string
}

variable "default_ami_id" {
  description = "Default AMI ID"
  type        = string
}

variable "environment" {
  description   = "Environment"
  type          = string
  default       = "dev"
}

variable "home_ip" {
  description   = "Home IP"
  type          = string
}

variable "aws_vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "name" {
  description = "Base name of the application"
  type        = string
  default     = "atomiklabs"
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
  description = "Neo4j resource prefix"
  type        = string
}

variable "private_subnets" {
  description = "Private subnets"
  type        = list(string)
}

variable "region" {
  description = "AWS region"
  type        = string
}

variable "tags" {
  description = "Tags"
  type        = map(string)
  default     = {}
}
