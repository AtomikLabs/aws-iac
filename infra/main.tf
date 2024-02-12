terraform {
  backend "s3" {
    bucket         = "atomiklabs-infra-config-bucket"
    key            = "terraform/terraform.state"
    region         = "us-east-1"
    dynamodb_table = "atomiklabs-terraform-locks"
    encrypt        = true
  }
}

module "network" {
  source             = "./network"
  REGION             = var.REGION
  ENVIRONMENT_NAME   = var.ENVIRONMENT_NAME
  VPC_CIDR           = var.VPC_CIDR
  SUBNET_CIDRS       = var.SUBNET_CIDRS
  AVAILABILITY_ZONES = var.AVAILABILITY_ZONES
}

module "containerization" {
  source             = "./containerization"
  REGION             = var.REGION
  ENVIRONMENT_NAME   = var.ENVIRONMENT_NAME
  VPC_ID             = module.network.VPC_ID
  PUBLIC_SUBNET_IDS  = module.network.PUBLIC_SUBNET_IDS
  PRIVATE_SUBNET_IDS = module.network.PRIVATE_SUBNET_IDS
  SECURITY_GROUP_ID  = module.network.SECURITY_GROUP_ID
}