# **********************************************************
# * TRIGGER                                                *
# **********************************************************
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