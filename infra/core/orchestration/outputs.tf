output "airflow_instance_id" {
  description = "ID of the Airflow instance"
  value       = aws_instance.orchestration_host.id
}