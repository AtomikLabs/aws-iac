resource "aws_iam_role" "fetch_daily_summaries_role" {
  name = "lambda_exec_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "fetch_daily_summaries_lambda_policy_attach" {
  role       = aws_iam_role.fetch_daily_summaries_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}


resource "aws_lambda_function" "fetch_daily_summaries" {
  function_name = "${local.environment}-fetch_daily_summaries"
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.repo.repository_url}:fetch_daily_summaries-latest"
  role          = aws_iam_role.fetch_daily_summaries_role.arn
  timeout       = 900
  memory_size   = 128
}