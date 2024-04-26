variable "app_name" {
  description = "Base name of the application"
  type        = string
  default     = "atomiklabs"
}

variable "availability_zones" {
  description = "Availability zones"
  type        = list(string)
}

variable "aws_vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "data_bucket" {
  description = "Data bucket"
  type        = string
}

variable "data_bucket_arn" {
  description = "Data bucket ARN"
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

variable "infra_config_bucket" {
  description = "Infra config bucket"
  type        = string
}

variable "infra_config_bucket_arn" {
  description = "ARN of the infra config bucket"
  type        = string
}

variable "orchestration_ami_id" {
  description = "orchestration AMI ID"
  type        = string
}

variable "orchestration_instance_type" {
  description = "orchestration instance type"
  type        = string
}

variable "orchestration_key_pair_name" {
  description = "orchestration key pair name"
  type        = string
}

variable "orchestration_resource_prefix" {
  description = "orchestration resource prefix"
  type        = string
}

variable "orchestration_source_security_group_ids" {
  description = "orchestration source security group IDs"
  type        = list(string)
}

variable "private_subnets" {
  description = "Private subnets"
  type        = list(string)
}

variable "region" {
  description = "AWS region"
  type        = string
}

variable "ssm_policy_for_instances_arn" {
  description = "SSM policy for instances ARN"
  type        = string
}

variable "tags" {
  description = "Tags"
  type        = map(string)
  default     = {}
}
