output "fetch_daily_summaries_security_group_id" {
  description = "Fetch daily summaries security group ID"
  value       = aws_security_group.fetch_daily_summaries_security_group.id
}

output "lambda_name" {
  description = "The name of the lambda function"
  value       = aws_lambda_function.fetch_daily_summaries.function_name
}