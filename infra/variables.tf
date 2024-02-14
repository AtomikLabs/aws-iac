variable "region" {
  description = "REGION"
  type        = string
  default     = "us-east-1"
}

variable "name" {
  description = "Name of the VPC and EKS Cluster"
  type        = string
  default     = "atomiklabs"
}

variable "eks_cluster_version" {
  description = "EKS Cluster version"
  type        = string
  default     = "1.29"
}

variable "vpc_cidr" {
  description = "VPC CIDR"
  type        = string
  default     = "10.1.0.0/16"
}

variable "enable_amazon_prometheus" {
  description = "Enable AWS Managed Prometheus service"
  type        = bool
  default     = true
}

variable "environment" {
  description = "Environment"
  type        = string
  default     = "dev"
}

variable "availability_zones" {
  description = "Availability Zones"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}
