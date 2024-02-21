# **********************************************************
# * GENERAL                                                *
# **********************************************************
resource "aws_iam_role" "fetch_daily_summaries_lambda_execution_role" {
  name = "${local.environment}-${local.fetch_daily_summaries_name}-lambda-execution-role"

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

# **********************************************************
# * TRIGGER                                                *
# **********************************************************
resource "aws_cloudwatch_event_rule" "fetch_daily_summaries" {
  name                = "${local.environment}-fetch_daily_summaries"
  description         = "Rule to trigger the fetch_daily_summaries lambda"
  schedule_expression = "cron(0 11 * * ? *)" # 3:00 AM PST
  role_arn            = aws_iam_role.eventbridge_role.arn
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

# **********************************************************
# * SERVICE                                                *
# **********************************************************
resource "aws_lambda_function" "fetch_daily_summaries" {
  function_name = "${local.environment}-${local.fetch_daily_summaries_name}"
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.repo.repository_url}:${local.environment}-${local.fetch_daily_summaries_name}-${local.fetch_daily_summaries_version}"
  role          = aws_iam_role.fetch_daily_summaries_lambda_execution_role.arn
  timeout       = 900
  memory_size   = 128

  environment {
    variables = {
      APP_NAME    = local.name
      ARXIV_BASE_URL = local.arxiv_base_url
      DATA_INGESTION_KEY_PREFIX = local.data_ingestion_key_prefix
      DATA_INGESTION_METADATA_KEY_PREFIX = local.data_ingestion_metadata_key_prefix
      ENVIRONMENT = local.environment
      GLUE_DATABASE_NAME = aws_glue_catalog_database.data_catalog_database.name
      GLUE_TABLE_NAME    = aws_glue_catalog_table.data_ingestion_metadata_table.name
      MAX_FETCH_ATTEMPTS = local.max_daily_summary_fetch_attempts
      S3_BUCKET_NAME   = aws_s3_bucket.atomiklabs_data_bucket.bucket
      S3_STORAGE_KEY_PREFIX = local.data_ingestion_key_prefix
      SERVICE_VERSION = local.fetch_daily_summaries_version
      SERVICE_NAME = local.fetch_daily_summaries_name
      SUMMARY_SET = local.arxiv_summary_set
    }  
  }
}

resource "aws_iam_policy" "basic_lambda_s3_access" {
  name        = "${local.environment}-fetch-daily-summaries-s3-access"
  description = "Allow Lambda to put objects in S3"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject",
          "s3:PutObjectAcl"
        ]
        Effect = "Allow",
        Resource = [
          "${aws_s3_bucket.atomiklabs_data_bucket.arn}/raw_data/data_ingestion/*",
          "${aws_s3_bucket.atomiklabs_data_bucket.arn}/metadata/*"
        ]
      },
      {
        Action = [
          "s3:ListBucket"
        ]
        Effect = "Allow",
        Resource = [
          "${aws_s3_bucket.atomiklabs_data_bucket.arn}"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.fetch_daily_summaries_lambda_execution_role.name
  policy_arn = local.AWSBasicExecutionRoleARN
}

resource "aws_iam_role_policy_attachment" "lambda_s3_access_attachment" {
  role       = aws_iam_role.fetch_daily_summaries_lambda_execution_role.name
  policy_arn = aws_iam_policy.basic_lambda_s3_access.arn
}

resource "aws_iam_role_policy_attachment" "lambda_glue_policy_attach" {
  role       = aws_iam_role.fetch_daily_summaries_lambda_execution_role.name
  policy_arn = aws_iam_policy.lambda_glue_policy.arn
}

resource "aws_lambda_permission" "allow_eventbridge_to_invoke_lambda" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.fetch_daily_summaries.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.fetch_daily_summaries.arn
}
