terraform {
  backend "s3" {
    bucket         = "atomiklabs-infra-config-bucket"
    dynamodb_table = "atomiklabs-parse-arxiv-summaries-locks"
    encrypt        = true
    key            = "terraform/services/parse_arxiv_summaries.state"
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
}

# **********************************************************
# * TRIGGER                                                *
# **********************************************************
resource "aws_s3_bucket_notification" "parse_arxiv_summaries_s3_trigger" {
  bucket = local.data_bucket

  lambda_function {
    lambda_function_arn = aws_lambda_function.parse_arxiv_summaries.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "raw_data/data_ingestion/"
    filter_suffix       = ".json"
  }

  depends_on = [
    aws_lambda_permission.allow_s3_bucket
  ]
}

resource "aws_lambda_permission" "allow_s3_bucket" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.parse_arxiv_summaries.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = "arn:aws:s3:::${local.data_bucket}/*"
}

# **********************************************************
# * SERVICE                                                *
# **********************************************************
resource "aws_lambda_function" "parse_arxiv_summaries" {
  function_name = "${local.environment}-${local.service_name}"
  package_type  = "Image"
  image_uri     = local.image_uri
  role          = aws_iam_role.parse_arxiv_summaries_lambda_execution_role.arn
  timeout       = 900
  memory_size   = 128

  environment {
    variables = {
      APP_NAME                              = local.app_name
      DATA_BUCKET                           = local.data_bucket
      ENVIRONMENT                           = local.environment
      SERVICE_VERSION                       = local.service_version
      SERVICE_NAME                          = local.service_name
    }  
  }
}

resource "aws_iam_role" "parse_arxiv_summaries_lambda_execution_role" {
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

resource "aws_iam_role_policy_attachment" "parse_arxiv_summaries_lambda_basic_execution" {
  role       = aws_iam_role.parse_arxiv_summaries_lambda_execution_role.name
  policy_arn = local.basic_execution_role_arn
}

resource "aws_iam_policy" "parse_arxiv_summaries_lambda_s3_access" {
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
          "${local.data_bucket_arn}/parsed_data/data_ingestion/*",
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

resource "aws_iam_role_policy_attachment" "parse_arxiv_summaries_lambda_s3_access_attachment" {
  role       = aws_iam_role.parse_arxiv_summaries_lambda_execution_role.name
  policy_arn = aws_iam_policy.parse_arxiv_summaries_lambda_s3_access.arn
}

resource "aws_iam_role_policy_attachment" "parse_arxiv_summaries_lambda_glue_policy_attach" {
  role       = aws_iam_role.parse_arxiv_summaries_lambda_execution_role.name
  policy_arn = aws_iam_policy.lambda_glue_policy.arn
}

resource "aws_iam_role_policy_attachment" "parse_arxiv_summaries_vpc_access_attachment" {
  role       = aws_iam_role.parse_arxiv_summaries_lambda_execution_role.name
  policy_arn = local.basic_execution_role_arn
}
