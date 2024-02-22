variable "app_name" {
  description = "Application name"
  type        = string
}

variable "availability_zones" {
  description = "Availability zones"
  type        = list(string)  
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "environment" {
  description = "Environment"
  type        = string
  default     = "dev"
}

variable "private_subnet_cidrs" {
  description = "CIDR for the private subnets"
  type        = list(string)
}

variable "public_subnet_cidrs" {
  description = "CIDR for the public subnets"
  type        = list(string)
}

variable "tags" {
  description = "Tags for the resources"
  type        = map(string)
}

variable "vpc_cidr" {
  description = "CIDR for the VPC"
  type        = string
}