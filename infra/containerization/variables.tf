variable "REGION" {
    type      = string
    description = "AWS region"
}

variable "ENVIRONMENT_NAME" {
  type        = string
  description = "Name of the deployment environment"
}

variable "VPC_ID" {
  type        = string
  description = "ID of the VPC"
}

variable "PUBLIC_SUBNET_IDS" {
  type        = list(string)
  description = "IDs of the public subnets"
}

variable "PRIVATE_SUBNET_IDS" {
  type        = list(string)
  description = "IDs of the private subnets"
}

variable "SECURITY_GROUP_ID" {
  type        = string
  description = "ID of the security group for public subnets"
}