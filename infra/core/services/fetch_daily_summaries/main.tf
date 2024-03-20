locals {
  app_name                    = var.app_name
  aws_region                  = var.aws_region
  aws_vpc_id                  = var.aws_vpc_id
  basic_execution_role_arn    = var.basic_execution_role_arn
  data_bucket                 = var.data_bucket
  data_bucket_arn             = var.data_bucket_arn
  environment                 = var.environment
  infra_config_bucket         = var.infra_config_bucket
  lambda_vpc_access_role      = var.lambda_vpc_access_role
  layer_data_management_arn   = var.layer_data_management_arn
  neo4j_password              = var.neo4j_password
  neo4j_uri                   = var.neo4j_uri
  neo4j_username              = var.neo4j_username
  private_subnets             = var.private_subnets
  runtime                     = var.runtime
  service_name                = var.service_name
  service_version             = var.service_version

  arxiv_base_url              = var.arxiv_base_url
  arxiv_summary_set           = var.arxiv_summary_set
  data_ingestion_key_prefix   = var.data_ingestion_key_prefix
  max_retries                 = var.max_retries
}

data "archive_file" "fetch_daily_summaries_lambda_function" {
  type       = "zip"
  source_dir  = "../../build/${local.service_name}"
  output_path = "../../build/${local.service_name}/${local.service_name}.zip"
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
  function_name     = "${local.environment}-${local.service_name}"
  filename          = data.archive_file.fetch_daily_summaries_lambda_function.output_path
  package_type      = "Zip"
  handler           = "lambda_handler.lambda_handler"
  role              = aws_iam_role.fetch_daily_summaries_lambda_execution_role.arn
  source_code_hash  = data.archive_file.fetch_daily_summaries_lambda_function.output_base64sha256
  timeout           = 900
  memory_size       = 256
  runtime           = local.runtime

  environment {
    variables = {
      APP_NAME                              = local.app_name
      ARXIV_BASE_URL                        = local.arxiv_base_url
      ARXIV_SUMMARY_SET                     = local.arxiv_summary_set
      DATA_BUCKET                           = local.data_bucket
      DATA_INGESTION_KEY_PREFIX             = local.data_ingestion_key_prefix
      ENVIRONMENT                           = local.environment
      MAX_RETRIES                           = local.max_retries
      NEO4J_PASSWORD                        = local.neo4j_password
      NEO4J_URI                             = local.neo4j_uri
      NEO4J_USERNAME                        = local.neo4j_username
      SERVICE_VERSION                       = local.service_version
      SERVICE_NAME                          = local.service_name
    }  
  }

  layers = [local.layer_data_management_arn]

  vpc_config {
    subnet_ids         = [local.private_subnets[0], local.private_subnets[1]]
    security_group_ids = [aws_security_group.fetch_daily_summaries_security_group.id]
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
          "${local.data_bucket_arn}/${local.data_ingestion_key_prefix}/*",
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

resource "aws_iam_policy" "fetch_daily_summaries_kms_decrypt" {
  name        = "${local.environment}-${local.service_name}-kms-decrypt"
  description = "Allow Lambda to decrypt KMS keys"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "kms:Decrypt"
        ]
        Effect = "Allow"
        Resource = [
          "*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "fetch_daily_summaries_lambda_s3_access_attachment" {
  role       = aws_iam_role.fetch_daily_summaries_lambda_execution_role.name
  policy_arn = aws_iam_policy.fetch_daily_summaries_lambda_s3_access.arn
}

resource "aws_iam_role_policy_attachment" "fetch_daily_summaries_vpc_access_attachment" {
  role       = aws_iam_role.fetch_daily_summaries_lambda_execution_role.name
  policy_arn = local.basic_execution_role_arn
}

resource "aws_iam_role_policy_attachment" "fetch_daily_summaries_kms_decrypt_attachment" {
  role       = aws_iam_role.fetch_daily_summaries_lambda_execution_role.name
  policy_arn = aws_iam_policy.fetch_daily_summaries_kms_decrypt.arn
}

resource "aws_security_group" "fetch_daily_summaries_security_group" {
  name_prefix = "${local.environment}-${local.service_name}-sg"
  vpc_id      = local.aws_vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.environment}-${local.service_name}-sg"
  }
}

resource "aws_iam_role_policy_attachment" "fetch_daily_summaries_lambda_vpc_access_attachment" {
  role       = aws_iam_role.fetch_daily_summaries_lambda_execution_role.name
  policy_arn = local.lambda_vpc_access_role
}
