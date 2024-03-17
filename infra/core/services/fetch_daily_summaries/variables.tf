variable "app_name" {
  description   = "The name of the application"
  type          = string
}

variable "arxiv_base_url" {
  description   = "The base URL for the arXiv API"
  type          = string
}

variable "arxiv_summary_set" {
  description   = "The set of arXiv summaries to fetch"
  type          = string
}

variable "aws_region" {
  description   = "The AWS region"
  type          = string
}

variable "aws_vpc_id" {
  description   = "The ID of the VPC"
  type          = string
}

variable "data_bucket" {
  description   = "The name of the S3 bucket where the data is stored"
  type          = string
}

variable "data_bucket_arn" {
  description   = "The ARN of the S3 bucket where the data is stored"
  type          = string
}

variable "data_ingestion_key_prefix" {
  description   = "The prefix for raw data in the data bucket"
  type          = string
}

variable "environment" {
  description   = "The environment where the service is deployed"
  type          = string
  default       = "dev"
}

variable "infra_config_bucket" {
  description   = "The name of the S3 bucket where the infrastructure configuration is stored"
  type          = string
}

variable "max_retries" {
  description   = "The maximum number of retries"
  type          = number
}

variable "neo4j_password" {
  description   = "The password for the Neo4j database"
  type          = string
}

variable "neo4j_uri" {
  description   = "The URI of the Neo4j database"
  type          = string
}

variable "neo4j_username" {
  description   = "The username for the Neo4j database"
  type          = string
}

variable "private_subnets" {
  description = "Private subnets"
  type        = list(string)
}

variable "runtime" {
  description   = "The runtime for the service"
  type          = string
}

variable "service_name" {
  description   = "The name of the service"
  type          = string
}

variable "service_version" {
  description   = "The version of the service"
  type          = string
}

variable "zip_key_prefix" {
  description   = "The key prefix for services zip files"
  type          = string
}




