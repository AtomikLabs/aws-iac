variable "REGION" {
    type      = string
    description = "AWS region"
}
variable "ENVIRONMENT_NAME" {
  type        = string
  description = "Name of the deployment environment"
}

variable "VPC_CIDR" {
  type        = string
  description = "CIDR block for the VPC"
}

variable "SUBNET_CIDRS" {
    type         = map(list(string))
    description  = "Map of subnet CIDRs"
}

variable "AVAILABILITY_ZONES" {
  type        = list(string)
  description = "List of availability zones in which to create subnets"
}

