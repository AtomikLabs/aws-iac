# **********************************************************
# * Data Ingestion                                         *
# **********************************************************
variable "arxiv_base_url" {
  description = "arXiv base URL"
  type        = string
}

variable "arxiv_summary_set" {
  description = "arXiv summary set to fetch"
  type        = string
  default     = "cs"
}

variable "data_ingestion_key_prefix" {
  description = "Prefix for the data ingestion"
  type        = string
}

variable "data_ingestion_metadata_key_prefix" {
  description = "Prefix for the data ingestion metadata"
  type        = string
}

variable "service_name" {
  description = "Fetch daily summaries service name"
  type        = string
}

variable "service_version" {
  description = "Fetch daily summaries service version"
  type        = string
}

variable "max_retries" {
  description = "Max daily summaries fetch attempts"
  type        = number
  default     = 10
}

# **********************************************************
# * Prototype                                              *
# **********************************************************

variable "prototype_name" {
  description = "Prototype name"
  type        = string
}

variable "prototype_version" {
  description = "Prototype version"
  type        = string
}

variable "prototype_max_attempts" {
  description = "Max daily summaries fetch attempts"
  type        = number
  default     = 10
}


# **********************************************************
# * ETL                                                    *
# **********************************************************

variable "etl_key_prefix" {
  description = "Prefix for the ETL"
  type        = string
}

# **********************************************************
# * INTEGRATIONS CONFIGURATION                             *
# **********************************************************

variable "openai_api_key" {
  description = "OpenAI API key"
  type        = string
}

variable "environment" {
  description = "Environment"
  type        = string
}