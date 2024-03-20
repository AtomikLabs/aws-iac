output "lambda_name" {
  description = "The name of the lambda function"
  value       = aws_lambda_function.parse_arxiv_summaries.function_name
}

output "parse_arxiv_summaries_security_group_id" {
  description = "Parse arXiv summaries security group ID"
  value       = aws_security_group.parse_arxiv_summaries_security_group.id
}