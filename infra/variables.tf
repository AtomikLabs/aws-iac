variable "region" {
  description = "AWS region to deploy the infrastructure"
  type        = string
  default     = "us-east-1"
}

variable "name" {
  description = "Base name of the application"
  type        = string
  default     = "atomiklabs"
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
