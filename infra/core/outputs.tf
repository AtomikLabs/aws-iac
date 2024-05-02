
# **********************************************************
# DATA MANAGEMENT                                          *
# **********************************************************
output "aws_iam_policy_s3_infra_config_bucket_access" {
    description = "IAM policy for S3 infra config bucket access"
    value       = module.data_management.aws_iam_policy_s3_infra_config_bucket_access
}

output "data_bucket" {
  description = "S3 bucket for atomiklabs data"
  value       = module.data_management.aws_s3_bucket_atomiklabs_data_bucket
}

output "data_bucket_arn" {
  description = "S3 bucket ARN for atomiklabs data"
  value       = module.data_management.aws_s3_bucket_atomiklabs_data_bucket_arn
}

output "neo4j_instance_private_ip" {
  description = "Private IP of Neo4j instance"
  value       = module.data_management.neo4j_instance_private_ip
}

# **********************************************************
# * ORCHESTRATION                                          *
# **********************************************************

output "orchestration_instance_id" {
  description = "ID of the orchestration instance"
  value       = module.orchestration.airflow_instance_id
}

output "orchestration_host_private_ip" {
  description = "Private IP of the orchestration host"
  value       = module.orchestration.orchestration_host_private_ip
}

# **********************************************************
# * NETWORKING                                             *
# **********************************************************
output "main_vpc_id" {
  value = module.networking.main_vpc_id
}

output "aws_private_subnet_ids" {
  value = module.networking.aws_private_subnet_ids
}

output "aws_public_subnet_ids" {
  value = module.networking.aws_public_subnet_ids
}

# **********************************************************
# * SCHEMAS                                                *
# **********************************************************
output "aws_glue_registry_name" {
  description = "Name of the Glue registry"
  value       = module.orchestration.aws_glue_registry_name
}

output "arxiv_research-ingestion-event-schema" {
  description = "Schema for arxiv research ingestion event"
  value       = module.orchestration.arxiv_research_ingestion_event_schema
}

# **********************************************************
# * TOPICS                                                 *
# **********************************************************
output "data-arxiv_summaries-ingestion-complete" {
  description = "Kafka topic for data-arxiv_summaries-ingestion-complete"
  value       = module.orchestration.kafka_topic_data_arxiv_summaries_ingestion_complete
}