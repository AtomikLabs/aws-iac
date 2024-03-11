variable "aws_ssm_managed_instance_core_arn" {
  description = "The ARN of the AmazonSSMManagedInstanceCore policy"
  type        = string
}

variable "bastion_host_key_pair_name" {
  description = "The name of the key pair to use for the bastion host"
  type        = string
}

variable "environment" {
  description = "The environment name"
  type        = string
}

variable "home_ip" {
  description = "The IP address of the user's home network"
  type        = string
}

variable "public_subnets" {
  description = "The IDs of the public subnets"
  type        = list(string)
}

variable "vpc_id" {
  description = "The ID of the VPC"
  type        = string
}
