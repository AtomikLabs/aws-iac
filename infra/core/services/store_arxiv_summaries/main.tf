locals {
  app_name                    = var.app_name
  aws_region                  = var.aws_region
  aws_vpc_id                  = var.aws_vpc_id
  basic_execution_role_arn    = var.basic_execution_role_arn
  data_bucket                 = var.data_bucket
  data_bucket_arn             = var.data_bucket_arn
  environment                 = var.environment
  etl_key_prefix              = var.etl_key_prefix
  lambda_vpc_access_role      = var.lambda_vpc_access_role
  services_layer_arn          = var.services_layer_arn
  neo4j_password              = var.neo4j_password
  neo4j_uri                   = var.neo4j_uri
  neo4j_username              = var.neo4j_username
  private_subnets             = var.private_subnets
  records_prefix              = var.records_prefix
  runtime                     = var.runtime
  service_name                = var.service_name
  service_version             = var.service_version
}

data "archive_file" "store_arxiv_summaries_lambda_function" {
  type       = "zip"
  source_dir = "../../build/${local.service_name}"
  output_path = "../../build/${local.service_name}/${local.service_name}.zip"
}

# **********************************************************
# * SERVICE                                                *
# **********************************************************
resource "aws_lambda_function" "store_arxiv_summaries" {
  function_name     = "${local.environment}-${local.service_name}"
  filename          = data.archive_file.store_arxiv_summaries_lambda_function.output_path
  package_type      = "Zip"
  handler           = "lambda_handler.lambda_handler"
  role              = aws_iam_role.store_arxiv_summaries_lambda_execution_role.arn
  source_code_hash  = data.archive_file.store_arxiv_summaries_lambda_function.output_base64sha256
  timeout           = 900
  memory_size       = 256
  runtime           = local.runtime

  environment {
    variables = {
      DATA_BUCKET                           = local.data_bucket
      NEO4J_PASSWORD                        = local.neo4j_password
      NEO4J_URI                             = local.neo4j_uri
      NEO4J_USERNAME                        = local.neo4j_username
      records_prefix                        = local.records_prefix
      SERVICE_VERSION                       = local.service_version
      SERVICE_NAME                          = local.service_name
    }  
  }

  layers = [local.services_layer_arn]

  vpc_config {
    subnet_ids         = local.private_subnets
    security_group_ids = [aws_security_group.store_arxiv_summaries_security_group.id]
  }
}

resource "aws_iam_role" "store_arxiv_summaries_lambda_execution_role" {
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

resource "aws_iam_role_policy_attachment" "store_arxiv_summaries_lambda_basic_execution" {
  role       = aws_iam_role.store_arxiv_summaries_lambda_execution_role.name
  policy_arn = local.basic_execution_role_arn
}

resource "aws_iam_policy" "store_arxiv_summaries_lambda_s3_access" {
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
          "${local.data_bucket_arn}/${local.records_prefix}/*",
          "${local.data_bucket_arn}/${local.etl_key_prefix}/*"
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

resource "aws_iam_policy" "store_arxiv_summaries_kms_decrypt" {
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

resource "aws_security_group" "store_arxiv_summaries_security_group" {
  name        = "${local.environment}-${local.service_name}-security-group"
  description = "Security group for the store arXiv summaries service"
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

resource "aws_iam_role_policy_attachment" "store_arxiv_summaries_lambda_s3_access_attachment" {
  role       = aws_iam_role.store_arxiv_summaries_lambda_execution_role.name
  policy_arn = aws_iam_policy.store_arxiv_summaries_lambda_s3_access.arn
}

resource "aws_iam_role_policy_attachment" "store_arxiv_summaries_vpc_access_attachment" {
  role       = aws_iam_role.store_arxiv_summaries_lambda_execution_role.name
  policy_arn = local.lambda_vpc_access_role
}

resource "aws_iam_role_policy_attachment" "store_arxiv_summaries_kms_decrypt_attachment" {
  role       = aws_iam_role.store_arxiv_summaries_lambda_execution_role.name
  policy_arn = aws_iam_policy.store_arxiv_summaries_kms_decrypt.arn
}