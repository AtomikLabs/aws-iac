variable "data_bucket" {
  description = "The name of the S3 bucket to store data"
  type = string
}

variable "data_bucket_arn" {
  description = "The ARN of the S3 bucket to store data"
  type = string
}

variable "data_ingestion_key_prefix" {
  description = "The prefix for the S3 key where data is ingested"
  type = string
}

variable "environment" {
  description = "The environment in which the infrastructure is deployed"
  type = string
}

variable "etl_key_prefix" {
  description = "The prefix for the S3 key where ETL data is stored"
  type = string
}

variable "parse_arxiv_summaries_name" {
  description = "The name of the Lambda function to parse ArXiv summaries"
  type = string
}

variable "parse_arxiv_summaries_arn" {
  description = "The ARN of the Lambda function to parse ArXiv summaries"
  type = string
}

variable "store_arxiv_summaries_name" {
  description = "The name of the Lambda function to store ArXiv summaries"
  type = string
}

variable "store_arxiv_summaries_arn" {
  description = "The ARN of the Lambda function to store ArXiv summaries"
  type = string
}
