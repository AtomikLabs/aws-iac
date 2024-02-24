output "aws_ecr_repository_arn" {
  value       = aws_ecr_repository.repo.arn
  description = "The Amazon Resource Name (ARN) that identifies the repository."
}

output "aws_ecr_repository_registry_id" {
  value       = aws_ecr_repository.repo.registry_id
  description = "The registry ID where the repository was created."
}

output "aws_ecr_repository_repository_url" {
  value       = aws_ecr_repository.repo.repository_url
  description = "The URL of the repository (in the form aws_account_id.dkr.ecr.region.amazonaws.com/repositoryName)."
}

output "aws_iam_policy_ecr_policy_arn" {
  value       = aws_iam_policy.ecr_policy.arn
  description = "The Amazon Resource Name (ARN) that identifies the policy."
}

output "aws_iam_role_ecr_role_arn" {
  value       = aws_iam_role.ecr_role.arn
  description = "The Amazon Resource Name (ARN) that identifies the role."
}

output "aws_iam_role_ecr_role_name" {
  value       = aws_iam_role.ecr_role.name
  description = "The name of the role."
}

output "aws_iam_policy_attachment_ecr_policy_attach_name" {
  value       = aws_iam_policy_attachment.ecr_policy_attach.name
  description = "The name of the policy attachment."
}

output "aws_iam_policy_attachment_ecr_policy_attach_policy_arn" {
  value       = aws_iam_policy_attachment.ecr_policy_attach.policy_arn
  description = "The Amazon Resource Name (ARN) that identifies the policy."
}

output "aws_s3_bucket_atomiklabs_data_bucket_arn" {
  value       = aws_s3_bucket.atomiklabs_data_bucket.arn
  description = "The Amazon Resource Name (ARN) that identifies the bucket."
}

output "aws_s3_bucket_atomiklabs_data_bucket_name" {
  value       = aws_s3_bucket.atomiklabs_data_bucket.bucket
  description = "The name of the bucket."
}

output "aws_lambda_function_fetch_daily_summaries_arn" {
  value       = aws_lambda_function.fetch_daily_summaries.arn
  description = "The Amazon Resource Name (ARN) that identifies the fetch daily summaries Lambda function."
}

output "aws_instance_bastion_public_ip" {
  value       = aws_instance.bastion_host.public_ip
  description = "The public IP address of the instance."
}

output "aws_instance_bastion_private_ip" {
  value       = aws_instance.bastion_host.private_ip
  description = "The private IP address of the instance."
}

output "aws_instance_rabbitmq_private_ips" {
  value       = aws_instance.rabbitmq[*].private_ip
  description = "The private IP addresses of the instances."
}

output "aws_instance_observer_private_ip" {
  value       = aws_instance.observer.private_ip
  description = "The private IP address of the instance."
}