variable "infra_config_bucket_arn" {
  description = "ARN of the infra config bucket"
  type        = string
}

variable "data_ingestion_metadata_key_prefix" {
    description = "Prefix for the data ingestion metadata"
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

variable "aws_vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "name" {
  description = "Base name of the application"
  type        = string
  default     = "atomiklabs"
}

variable "tags" {
  description = "Tags"
  type        = map(string)
  default     = {}
}
