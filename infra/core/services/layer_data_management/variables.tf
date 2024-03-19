variable "app_name" {
    description   = "The name of the application"
    type          = string
}

variable "aws_region" {
    description   = "The AWS region"
    type          = string
}

variable "environment" {
    description   = "The environment where the service is deployed"
    type          = string
}

variable "runtime" {
    description   = "The runtime for the service"
    type          = string
}

variable "service_name" {
    description   = "The name of the service"
    type          = string
}

variable "service_version" {
    description   = "The version of the service"
    type          = string
}
