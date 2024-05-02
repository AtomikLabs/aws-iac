output "airflow_instance_id" {
  description = "ID of the Airflow instance"
  value       = aws_instance.orchestration_host.id
}

output "arxiv_research_ingestion_event_schema" {
  description = "Schema for arxiv research ingestion event"
  value       = aws_glue_schema.arxiv_research_ingestion_event_schema.schema_name
}

output "aws_glue_registry_arn" {
  description = "ARN of the Glue registry"
  value       = aws_glue_registry.glue-registry.arn
}

output "aws_glue_registry_id" {
  description = "ID of the Glue registry"
  value       = aws_glue_registry.glue-registry.id
}

output "aws_glue_registry_name" {
  description = "Name of the Glue registry"
  value       = aws_glue_registry.glue-registry.registry_name
}

output "data-arxiv_summaries-ingestion-complete" {
  description = "Kafka topic for data-arxiv_summaries-ingestion-complete"
  value       = kafka_topic.data_arxiv_summaries_ingestion_complete.name
}

output "orchestration_host_private_ip" {
  description = "Private IP of the orchestration host"
  value       = aws_instance.orchestration_host.private_ip
}

output "orchestration_security_group_id" {
  description = "ID of the security group for the orchestration host"
  value       = aws_security_group.orchestration_security_group.id
}