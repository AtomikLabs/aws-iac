locals {
  app_name                    = var.app_name
  aws_region                  = var.aws_region
  aws_vpc_id                  = var.aws_vpc_id
  basic_execution_role_arn    = var.basic_execution_role_arn
  dispatch_lambda_names       = var.dispatch_lambda_names
  environment                 = var.environment
  lambda_vpc_access_role      = var.lambda_vpc_access_role
  private_subnets             = var.private_subnets
  services_layer_arn          = var.services_layer_arn
  runtime                     = var.runtime
  service_name                = var.service_name
  service_version             = var.service_version
}

data "archive_file" "post_arxiv_parse_dispatcher_lambda_function" {
  type       = "zip"
  source_dir = "../../build/${local.service_name}"
  output_path = "../../build/${local.service_name}/${local.service_name}.zip"
}

# **********************************************************
# * SERVICE                                                *
# **********************************************************
resource "aws_lambda_function" "post_arxiv_parse_dispatcher" {
  function_name     = "${local.environment}-${local.service_name}"
  filename          = data.archive_file.post_arxiv_parse_dispatcher_lambda_function.output_path
  package_type      = "Zip"
  handler           = "lambda_handler.lambda_handler"
  role              = aws_iam_role.post_arxiv_parse_dispatcher_lambda_execution_role.arn
  source_code_hash  = data.archive_file.post_arxiv_parse_dispatcher_lambda_function.output_base64sha256
  timeout           = 900
  memory_size       = 256
  runtime           = local.runtime

  environment {
    variables = {
      DISPATCH_LAMBDA_NAMES                 = jsonencode(local.dispatch_lambda_names)
      SERVICE_VERSION                       = local.service_version
      SERVICE_NAME                          = local.service_name
    }  
  }

  layers = [local.services_layer_arn]

  vpc_config {
    subnet_ids         = local.private_subnets
    security_group_ids = [aws_security_group.post_arxiv_parse_dispatcher_security_group.id]
  }
}

resource "aws_iam_role" "post_arxiv_parse_dispatcher_lambda_execution_role" {
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

resource "aws_iam_role_policy_attachment" "post_arxiv_parse_dispatcher_lambda_basic_execution" {
  role       = aws_iam_role.post_arxiv_parse_dispatcher_lambda_execution_role.name
  policy_arn = local.basic_execution_role_arn
}

resource "aws_iam_policy" "post_arxiv_parse_dispatcher_kms_decrypt" {
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

resource "aws_security_group" "post_arxiv_parse_dispatcher_security_group" {
  name        = "${local.environment}-${local.service_name}-security-group"
  description = "Security group for the post arXiv parse dispatcher service"
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

resource "aws_iam_role_policy_attachment" "post_arxiv_parse_dispatcher_vpc_access_attachment" {
  role       = aws_iam_role.post_arxiv_parse_dispatcher_lambda_execution_role.name
  policy_arn = local.lambda_vpc_access_role
}

resource "aws_iam_role_policy_attachment" "post_arxiv_parse_dispatcher_kms_decrypt_attachment" {
  role       = aws_iam_role.post_arxiv_parse_dispatcher_lambda_execution_role.name
  policy_arn = aws_iam_policy.post_arxiv_parse_dispatcher_kms_decrypt.arn
}
