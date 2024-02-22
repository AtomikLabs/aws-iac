variable "app_name" {
  description = "The name of the application"
  type        = string
}

variable "aws_region" {
  description = "The AWS region to deploy the infrastructure"
  type        = string
}

variable "data_ingestion_metadata_key_prefix" {
  description = "The prefix for the data ingestion metadata keys"
  type        = string
}

variable "environment" {
  description = "The environment to deploy the infrastructure"
  type        = string
}

variable "tags" {
  description = "The tags to apply to all resources"
  type        = map(string)
}