output "airflow_instance_id" {
  description = "ID of the Airflow instance"
  value       = aws_instance.orchestration_host.id
}

output "orchestration_security_group_id" {
  description = "ID of the security group for the orchestration host"
  value       = aws_security_group.orchestration_security_group.id
}