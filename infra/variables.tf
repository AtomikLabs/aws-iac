variable "ENVIRONMENT_NAME" {
  type        = string
  description = "Name of the deployment environment"
}

variable "VPC_CIDR" {
  type        = string
  description = "CIDR block for the VPC"
}

variable "PUBLIC_SUBNET_1_CIDR" {
  type        = string
  description = "CIDR block for the first public subnet"
}

variable "PUBLIC_SUBNET_2_CIDR" {
  type        = string
  description = "CIDR block for the second public subnet"
}

variable "PRIVATE_SUBNET_1_CIDR" {
  type        = string
  description = "CIDR block for the first private subnet"
}

variable "PRIVATE_SUBNET_2_CIDR" {
  type        = string
  description = "CIDR block for the second private subnet"
}
