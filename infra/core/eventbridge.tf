resource "aws_cloudwatch_event_rule" "fetch_daily_summaries" {
  name                = "${local.environment}-fetch_daily_summaries"
  description         = "Rule to trigger the fetch_daily_summaries lambda"
  schedule_expression = "cron(0 11 * * ? *)" # 3:00 AM PST
}

resource "aws_cloudwatch_event_target" "fetch_daily_summaries_target" {
  rule      = aws_cloudwatch_event_rule.fetch_daily_summaries.name
  arn       = aws_lambda_function.fetch_daily_summaries.arn
}

resource "aws_iam_policy" "eventbridge_policy" {
  name        = "${local.environment}-event_bridge_policy"
  path        = "/"
  description = "Policy to allow triggering lambdas from eventbridge"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = "lambda:InvokeFunction",
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role" "eventbridge_role" {
  name = "${local.environment}-event_bridge_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "events.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_policy_attachment" "eventbridge_policy_attach" {
  name       = "${local.environment}-event_bridge_policy_attachment"
  roles      = [aws_iam_role.eventbridge_role.name]
  policy_arn = aws_iam_policy.eventbridge_policy.arn
}