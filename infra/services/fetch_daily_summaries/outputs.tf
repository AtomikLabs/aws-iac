output "lambda_name" {
  description = "The name of the lambda function"
  value       = aws_lambda_function.fetch_daily_summaries.function_name
}