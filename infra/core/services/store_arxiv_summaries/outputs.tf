output "lambda_name" {
  description = "The name of the lambda function"
  value       = aws_lambda_function.store_arxiv_summaries.function_name
}

output "lambda_arn" {
  description = "The ARN of the lambda function"
  value       = aws_lambda_function.store_arxiv_summaries.arn
}

output "store_arxiv_summaries_security_group_id" {
  description = "Parse arXiv summaries security group ID"
  value       = aws_security_group.store_arxiv_summaries_security_group.id
}