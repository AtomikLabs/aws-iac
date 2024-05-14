output "lambda_name" {
  description = "The name of the lambda function"
  value       = aws_lambda_function.post_arxiv_parse_dispatcher.function_name
}

output "lambda_arn" {
  description = "The ARN of the lambda function"
  value       = aws_lambda_function.post_arxiv_parse_dispatcher.arn
}

output "post_arxiv_parse_dispatcher_security_group_id" {
  description = "Parse arXiv summaries security group ID"
  value       = aws_security_group.post_arxiv_parse_dispatcher_security_group.id
}