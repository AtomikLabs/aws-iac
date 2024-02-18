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
# * fetch_daily_summaries                                  *
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
      ENVIRONMENT = local.environment
      DATA_INGESTION_METADATA_KEY_PREFIX = local.data_ingestion_metadata_key_prefix
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
          "${aws_s3_bucket.atomiklabs_data_bucket.arn}/data_ingestion/*",
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
