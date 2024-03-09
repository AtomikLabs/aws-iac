variable "app_name" {
  description   = "The name of the application"
  type          = string
}

variable "aws_region" {
  description   = "The AWS region"
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

variable "data_catalog_db_name" {
  description   = "The name of the data catalog database"
  type          = string
}

variable "environment" {
  description   = "The environment where the service is deployed"
  type          = string
  default       = "dev"
}

variable "image_uri" {
  description   = "The name of the Docker image"
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





