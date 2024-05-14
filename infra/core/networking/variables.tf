variable "availability_zone_available_names" {
  description = "Availability zone names"
  type        = list(string)
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

