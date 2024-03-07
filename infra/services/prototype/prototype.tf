# **********************************************************
# * TRIGGER                                                *
# **********************************************************
resource "aws_cloudwatch_event_rule" "prototype" {
  name                = "${local.environment}-prototype"
  description         = "Rule to trigger the prototype lambda"
  schedule_expression = "cron(0 11 * * ? *)" # 3:00 AM PST
  role_arn            = aws_iam_role.eventbridge_role.arn
}

resource "aws_cloudwatch_event_target" "prototype_target" {
  rule      = aws_cloudwatch_event_rule.prototype.name
  arn       = aws_lambda_function.prototype.arn
}

resource "aws_lambda_permission" "allow_eventbridge_to_invoke_prototype" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.prototype.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.prototype.arn
}

# **********************************************************
# * SERVICE                                                *
# **********************************************************
resource "aws_lambda_function" "prototype" {
  function_name = "${local.environment}-${local.prototype_name}"
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.repo.repository_url}:${local.environment}-${local.prototype_name}-${local.prototype_version}"
  role          = aws_iam_role.prototype_lambda_execution_role.arn
  timeout       = 900
  memory_size   = 128
  vpc_config {
    subnet_ids         = [aws_subnet.private[0].id, aws_subnet.private[1].id]
    security_group_ids = [aws_security_group.lambda_sg.id]
  }

  environment {
    variables = {
      APP_NAME                            = local.name
      ARXIV_BASE_URL                      = local.arxiv_base_url
      DATA_INGESTION_KEY_PREFIX           = local.data_ingestion_key_prefix
      DATA_INGESTION_METADATA_KEY_PREFIX  = local.data_ingestion_metadata_key_prefix
      ENVIRONMENT                         = local.environment
      GLUE_DATABASE_NAME                  = aws_glue_catalog_database.data_catalog_database.name
      GLUE_TABLE_NAME                     = aws_glue_catalog_table.data_ingestion_metadata_table.name
      MAX_FETCH_ATTEMPTS                  = local.max_daily_summary_fetch_attempts
      OPENAI_API_KEY                      = local.openai_api_key
      S3_BUCKET_NAME                      = aws_s3_bucket.atomiklabs_data_bucket.bucket
      S3_STORAGE_KEY_PREFIX               = local.data_ingestion_key_prefix
      SERVICE_VERSION                     = local.prototype_version
      SERVICE_NAME                        = local.prototype_name
      SUMMARY_SET                         = local.arxiv_summary_set
    }  
  }
}

resource "aws_iam_role" "prototype_lambda_execution_role" {
  name = "${local.environment}-${local.prototype_name}-lambda-execution-role"

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

resource "aws_iam_role_policy_attachment" "prototype_lambda_basic_execution" {
  role       = aws_iam_role.prototype_lambda_execution_role.name
  policy_arn = local.AWSBasicExecutionRoleARN
}

resource "aws_iam_policy" "prototype_lambda_s3_access" {
  name        = "${local.environment}-${local.prototype_name}-lambda-s3-access"
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

resource "aws_iam_role_policy_attachment" "prototype_lambda_s3_access_attachment" {
  role       = aws_iam_role.prototype_lambda_execution_role.name
  policy_arn = aws_iam_policy.prototype_lambda_s3_access.arn
}

resource "aws_iam_role_policy_attachment" "prototype_lambda_glue_policy_attach" {
  role       = aws_iam_role.prototype_lambda_execution_role.name
  policy_arn = aws_iam_policy.lambda_glue_policy.arn
}

resource "aws_iam_role_policy_attachment" "prototype_vpc_access_attachment" {
  role       = aws_iam_role.prototype_lambda_execution_role.name
  policy_arn = local.AWSLambdaVPCAccessExecutionRole
}
