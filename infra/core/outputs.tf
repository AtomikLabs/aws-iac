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

output "bucket_name" {
  value = aws_s3_bucket.data.bucket
}

output "bucket_arn" {
  value = aws_s3_bucket.data.arn
}