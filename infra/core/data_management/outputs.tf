output "aws_iam_policy_s3_infra_config_bucket_access" {
    description = "IAM policy for S3 infra config bucket access"
    value       = aws_iam_policy.s3_infra_config_bucket_access.arn
}

output "aws_s3_bucket_atomiklabs_data_bucket" {
  description = "S3 bucket for atomiklabs data"
  value       = aws_s3_bucket.atomiklabs_data_bucket.bucket
}

output "aws_s3_bucket_atomiklabs_data_bucket_arn" {
  description = "S3 bucket ARN for atomiklabs data"
  value       = aws_s3_bucket.atomiklabs_data_bucket.arn
}

output "neo4j_instance_private_ip" {
  description = "Private IP of Neo4j instance"
  value       = aws_instance.neo4j_host.private_ip
}

output "neo4j_security_group_id" {
  description = "Security group ID for Neo4j instance"
  value       = aws_security_group.neo4j_security_group.id
}