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