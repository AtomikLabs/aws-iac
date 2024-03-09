output "lambda_name" {
  description = "The name of the lambda function"
  value       = aws_lambda_function.parse_arxiv_summaries.function_name
}