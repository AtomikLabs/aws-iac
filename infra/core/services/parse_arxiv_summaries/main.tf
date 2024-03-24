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
  aws_vpc_id                  = var.aws_vpc_id
  basic_execution_role_arn    = var.basic_execution_role_arn
  data_bucket                 = var.data_bucket
  data_bucket_arn             = var.data_bucket_arn
  data_ingestion_key_prefix   = var.data_ingestion_key_prefix
  environment                 = var.environment
  etl_key_prefix              = var.etl_key_prefix
  lambda_vpc_access_role      = var.lambda_vpc_access_role
  layer_data_management_arn   = var.layer_data_management_arn
  neo4j_password              = var.neo4j_password
  neo4j_uri                   = var.neo4j_uri
  neo4j_username              = var.neo4j_username
  private_subnets             = var.private_subnets
  runtime                     = var.runtime
  service_name                = var.service_name
  service_version             = var.service_version
}

data "archive_file" "parse_arxiv_summaries_lambda_function" {
  type       = "zip"
  source_dir = "../../build/${local.service_name}"
  output_path = "../../build/${local.service_name}/${local.service_name}.zip"
}

# **********************************************************
# * TRIGGER                                                *
# **********************************************************
resource "aws_s3_bucket_notification" "parse_arxiv_summaries_s3_trigger" {
  bucket = local.data_bucket

  lambda_function {
    lambda_function_arn = "arn:aws:lambda:us-east-1:758145997264:function:${local.environment}-${local.service_name}"
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = local.data_ingestion_key_prefix
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
  source_arn    = "${local.data_bucket_arn}"
}

# **********************************************************
# * SERVICE                                                *
# **********************************************************
resource "aws_lambda_function" "parse_arxiv_summaries" {
  function_name     = "${local.environment}-${local.service_name}"
  filename          = data.archive_file.parse_arxiv_summaries_lambda_function.output_path
  package_type      = "Zip"
  handler           = "lambda_handler.lambda_handler"
  role              = aws_iam_role.parse_arxiv_summaries_lambda_execution_role.arn
  source_code_hash  = data.archive_file.parse_arxiv_summaries_lambda_function.output_base64sha256
  timeout           = 900
  memory_size       = 256
  runtime           = local.runtime

  environment {
    variables = {
      APP_NAME                              = local.app_name
      DATA_BUCKET                           = local.data_bucket
      ENVIRONMENT                           = local.environment
      ETL_KEY_PREFIX                        = local.etl_key_prefix
      NEO4J_PASSWORD                        = local.neo4j_password
      NEO4J_URI                             = local.neo4j_uri
      NEO4J_USERNAME                        = local.neo4j_username
      SERVICE_VERSION                       = local.service_version
      SERVICE_NAME                          = local.service_name
    }  
  }

  layers = [local.layer_data_management_arn]

  vpc_config {
    subnet_ids         = local.private_subnets
    security_group_ids = [aws_security_group.parse_arxiv_summaries_security_group.id]
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

resource "aws_iam_policy" "parse_arxivc_summaries_lambda_s3_access" {
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
          "${local.data_bucket_arn}/${local.etl_key_prefix}/*",
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

resource "aws_iam_policy" "parse_arxivc_summaries_kms_decrypt" {
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

resource "aws_security_group" "parse_arxiv_summaries_security_group" {
  name        = "${local.environment}-${local.service_name}-security-group"
  description = "Security group for the parse arXiv summaries service"
  vpc_id      = local.aws_vpc_id

  egress {
    from_port  = 0
    to_port    = 0
    protocol   = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.environment}-${local.service_name}-sg"
  }
}


resource "aws_iam_role_policy_attachment" "parse_arxivc_summaries_lambda_s3_access_attachment" {
  role       = aws_iam_role.parse_arxiv_summaries_lambda_execution_role.name
  policy_arn = aws_iam_policy.parse_arxivc_summaries_lambda_s3_access.arn
}

resource "aws_iam_role_policy_attachment" "parse_arxiv_summaries_vpc_access_attachment" {
  role       = aws_iam_role.parse_arxiv_summaries_lambda_execution_role.name
  policy_arn = local.lambda_vpc_access_role
}

resource "aws_iam_role_policy_attachment" "parse_arxiv_summaries_kms_decrypt_attachment" {
  role       = aws_iam_role.parse_arxiv_summaries_lambda_execution_role.name
  policy_arn = aws_iam_policy.parse_arxivc_summaries_kms_decrypt.arn
}