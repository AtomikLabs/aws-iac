variable "app_name" {
  description   = "The name of the application"
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

variable "basic_execution_role_arn" {
  description   = "The ARN of the basic execution role"
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
  description   = "The prefix for the data ingestion keys"
  type          = string
}

variable "environment" {
  description   = "The environment where the service is deployed"
  type          = string
  default       = "dev"
}

variable "etl_key_prefix" {
  description   = "The prefix for the ETL keys"
  type          = string
}

variable "lambda_vpc_access_role" {
  description   = "The ARN of the role that allows the Lambda function to access the VPC"
  type          = string
}

variable "neo4j_password" {
  description   = "The password for the Neo4j database"
  type          = string
}

variable "neo4j_uri" {
  description   = "The URI for the Neo4j database"
  type          = string
}

variable "neo4j_username" {
  description   = "The username for the Neo4j database"
  type          = string
}

variable "private_subnets" {
  description   = "The private subnets"
  type          = list(string)
}

variable "runtime" {
  description   = "The runtime for the Lambda function"
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





