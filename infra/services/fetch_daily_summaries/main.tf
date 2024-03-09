terraform {
  backend "s3" {
    bucket         = "atomiklabs-infra-config-bucket"
    dynamodb_table = "atomiklabs-fetch-daily-summaries-locks"
    encrypt        = true
    key            = "terraform/services/fetch_daily_summaries.state"
    region         = "us-east-1"
  }
}

locals {
  app_name                    = var.app_name
  aws_region                  = var.aws_region
  basic_execution_role_arn    = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  data_bucket                 = var.data_bucket
  data_bucket_arn             = "arn:aws:s3:::${var.data_bucket}"
  environment                 = var.environment
  image_uri                   = var.image_uri
  service_name                = var.service_name
  service_version             = var.service_version

  arxiv_base_url                          = var.arxiv_base_url
  arxiv_summary_set                       = var.arxiv_summary_set
  data_ingestion_key_prefix               = var.data_ingestion_key_prefix
  data_ingestion_metadata_key_prefix      = var.data_ingestion_metadata_key_prefix
  data_catalog_db_name                    = var.data_catalog_db_name
  metadata_table_name                     = var.metadata_table_name
  max_retries                             = var.max_retries
}


# **********************************************************
# * TRIGGER                                                *
# **********************************************************
resource "aws_cloudwatch_event_rule" "fetch_daily_summaries" {
  name                = "${local.environment}-${local.service_name}"
  description         = "Rule to trigger the ${local.service_name} lambda"
  schedule_expression = "cron(0 11 * * ? *)" # 3:00 AM PST
  role_arn            = aws_iam_role.eventbridge_role.arn
}

resource "aws_cloudwatch_event_target" "fetch_daily_summaries_target" {
  rule      = aws_cloudwatch_event_rule.fetch_daily_summaries.name
  arn       = aws_lambda_function.fetch_daily_summaries.arn
}

resource "aws_lambda_permission" "allow_eventbridge_to_invoke_fetch_daily_summaries" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.fetch_daily_summaries.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.fetch_daily_summaries.arn
}

resource "aws_iam_policy" "eventbridge_policy" {
  name        = "${local.environment}-${local.service_name}-event_bridge_policy"
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
  name = "${local.environment}-${local.service_name}-event_bridge_role"

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
  name       = "${local.environment}-${local.service_name}-event_bridge_policy_attachment"
  roles      = [aws_iam_role.eventbridge_role.name]
  policy_arn = aws_iam_policy.eventbridge_policy.arn
}

# **********************************************************
# * SERVICE                                                *
# **********************************************************
resource "aws_lambda_function" "fetch_daily_summaries" {
  function_name = "${local.environment}-${local.service_name}"
  package_type  = "Image"
  image_uri     = local.image_uri
  role          = aws_iam_role.fetch_daily_summaries_lambda_execution_role.arn
  timeout       = 900
  memory_size   = 128

  environment {
    variables = {
      APP_NAME                              = local.app_name
      ARXIV_BASE_URL                        = local.arxiv_base_url
      ARXIV_SUMMARY_SET                     = local.arxiv_summary_set
      DATA_BUCKET                           = local.data_bucket
      DATA_INGESTION_KEY_PREFIX             = local.data_ingestion_key_prefix
      DATA_INGESTION_METADATA_KEY_PREFIX    = local.data_ingestion_metadata_key_prefix
      ENVIRONMENT                           = local.environment
      DATA_CATALOG_DB_NAME                  = local.data_catalog_db_name
      METADATA_TABLE_NAME                   = local.metadata_table_name
      MAX_RETRIES                           = local.max_retries
      SERVICE_VERSION                       = local.service_version
      SERVICE_NAME                          = local.service_name
    }  
  }
}

resource "aws_iam_role" "fetch_daily_summaries_lambda_execution_role" {
  name = "${local.environment}-${local.service_name}-lambda-execution-role"

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

resource "aws_iam_role_policy_attachment" "fetch_daily_summaries_lambda_basic_execution" {
  role       = aws_iam_role.fetch_daily_summaries_lambda_execution_role.name
  policy_arn = local.basic_execution_role_arn
}

resource "aws_iam_policy" "fetch_daily_summaries_lambda_s3_access" {
  name        = "${local.environment}-${local.service_name}-lambda-s3-access"
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
          "${local.data_bucket_arn}/raw_data/data_ingestion/*",
          "${local.data_bucket_arn}/metadata/*"
        ]
      },
      {
        Action = [
          "s3:ListBucket"
        ]
        Effect = "Allow",
        Resource = [
          "${local.data_bucket_arn}"
        ]
      }
    ]
  })
}

resource "aws_iam_policy" "lambda_glue_policy" {
  name        = "${local.environment}-${local.service_name}-lambda_glue_data_catalog_access_policy"
  description = "IAM policy for accessing AWS Glue Data Catalog from Lambda"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = [
          "glue:GetDatabase",
          "glue:GetDatabases",
          "glue:GetTable",
          "glue:GetTables",
          "glue:SearchTables",
          "glue:GetPartitions",
          "glue:GetPartition",
          "glue:StartCrawler",
          "glue:UpdateTable",
          "glue:CreateTable",
        ],
        Effect   = "Allow",
        Resource = "*"
      },
    ],
  })
}

resource "aws_iam_role_policy_attachment" "fetch_daily_summaries_lambda_s3_access_attachment" {
  role       = aws_iam_role.fetch_daily_summaries_lambda_execution_role.name
  policy_arn = aws_iam_policy.fetch_daily_summaries_lambda_s3_access.arn
}

resource "aws_iam_role_policy_attachment" "fetch_daily_summaries_lambda_glue_policy_attach" {
  role       = aws_iam_role.fetch_daily_summaries_lambda_execution_role.name
  policy_arn = aws_iam_policy.lambda_glue_policy.arn
}

resource "aws_iam_role_policy_attachment" "fetch_daily_summaries_vpc_access_attachment" {
  role       = aws_iam_role.fetch_daily_summaries_lambda_execution_role.name
  policy_arn = local.basic_execution_role_arn
}
