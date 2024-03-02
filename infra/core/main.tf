terraform {
  backend "s3" {
    bucket         = "atomiklabs-infra-config-bucket"
    key            = "terraform/terraform.state"
    region         = "us-east-1"
    dynamodb_table = "atomiklabs-terraform-locks"
    encrypt        = true
  }
}

data "aws_availability_zones" "available" {}
data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

locals {
  # **********************************************************
  # * AWS ACCOUNT                                            *
  # **********************************************************
  account_id                = data.aws_caller_identity.current.account_id
  aws_region                = var.aws_region
  partition                 = data.aws_partition.current.partition
  
  # **********************************************************
  # * INFRASTRUCTURE CONFIGURATION                           *
  # **********************************************************
  alert_email                     = var.alert_email
  backend_dynamodb_table          = var.backend_dynamodb_table
  environment                     = var.environment
  iam_user_name                   = var.iam_user_name
  infra_config_bucket             = var.infra_config_bucket
  infra_config_bucket_arn         = var.infra_config_bucket_arn
  infra_config_prefix             = var.infra_config_prefix
  name                            = var.name
  outputs_prefix                  = var.outputs_prefix
  repo                            = var.repo
  
  # **********************************************************
  # * INTEGRATIONS CONFIGURATION                             *
  # **********************************************************

  openai_api_key                  = var.openai_api_key

  # **********************************************************
  # * SERVICES CONFIGURATION                                 *
  # **********************************************************
  AWSBasicExecutionRoleARN                  = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  AWSLambdaVPCAccessExecutionRole           = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
  AmazonSSMManagedInstanceCoreARN           = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
  AmazonSSMManagedEC2InstanceDefaultPolicy  = "arn:aws:iam::aws:policy/AmazonSSMManagedEC2InstanceDefaultPolicy"
  
  # **********************************************************
  # * DATA INGESTION CONFIGURATION                           *
  # **********************************************************
  arxiv_base_url                          = var.arxiv_base_url
  arxiv_summary_set                       = var.arxiv_summary_set
  data_ingestion_key_prefix               = var.data_ingestion_key_prefix
  fetch_daily_summaries_name              = var.fetch_daily_summaries_name
  fetch_daily_summaries_version           = var.fetch_daily_summaries_version
  max_daily_summary_fetch_attempts        = var.fetch_daily_summaries_max_attempts

  # **********************************************************
  # * PROTOTYPE CONFIGURATION                                *
  # **********************************************************

  prototype_name                          = var.prototype_name
  prototype_version                       = var.prototype_version
  max_daily_prototype_attempts            = var.prototype_max_attempts

  # **********************************************************
  # * ETL CONFIGURATION                                      *
  # **********************************************************

  etl_key_prefix                    = var.etl_key_prefix
  AWSGlueServiceRoleARN             = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"

  # **********************************************************
  # * METADATA CONFIGURATION                                 *
  # **********************************************************
  data_ingestion_metadata_key_prefix = var.data_ingestion_metadata_key_prefix

  # **********************************************************
  # * NETWORKING CONFIGURATION                               *
  # **********************************************************

  bastion_host_key_pair_name        = var.bastion_host_key_pair_name
  home_ip                           = "${var.home_ip}/32"

  # **********************************************************
  # * MESSAGING CONFIGURATION                                *
  # **********************************************************
  rabbitmqctl_username              = var.rabbitmqctl_username
  rabbitmqctl_password              = var.rabbitmqctl_password
  
  tags = {
    Blueprint   = local.name
    GithubRepo  = local.repo
    Environment = local.environment
    Region      = local.aws_region
    Application = local.name
  }
}

resource "aws_iam_policy" "s3_infra_config_bucket_access" {
  name        = "${local.environment}-s3-infra-config-bucket-access"
  description = "Allow access to the infra config bucket"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject",
          "s3:PutObjectAcl"
        ]
        Effect   = "Allow"
        Resource = "${local.infra_config_bucket_arn}/*"
      },
      {
        Action   = "s3:ListBucket"
        Effect   = "Allow"
        Resource = "${local.infra_config_bucket_arn}"
      },
    ],
  })
}

resource "aws_iam_role" "ssm_managed_instance_role" {
  name = "ssm-managed-instance-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_policy" "ssm_manager" {
  name        = "ssm-manager"
  description = "Allow SSM to manage instances"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = [
          "ssm:*"
        ],
        Effect   = "Allow",
        Resource = "*"
      },
    ],
  })
}

resource "aws_iam_role_policy_attachment" "ssm_managed_instance_role_ssm_manager" {
  role       = aws_iam_role.ssm_managed_instance_role.name
  policy_arn = aws_iam_policy.ssm_manager.arn
}

resource "aws_iam_policy" "ssm_policy_for_instances" {
  name        = "ssm-policy-for-instances"
  description = "Allow SSM to manage instances"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = [
          "ssm:UpdateInstanceInformation",
          "ssm:ListInstanceAssociations",
          "ssm:DescribeInstanceInformation",
          "ssm:SendCommand",
          "ssm:ListCommands",
          "ssm:GetCommandInvocation",
          "ssm:ListCommandInvocations",
          "ssm:CancelCommand",
          "ssm:GetCommandInvocation",
          "ssm:ListCommandInvocations",
          "ssm:CancelCommand",
          "ssm:ListCommands",
          "ssm:SendCommand",
          "ssm:DescribeInstanceInformation",
          "ssm:ListInstanceAssociations",
          "ssm:UpdateInstanceInformation"
        ],
        Effect   = "Allow",
        Resource = "*"
      },
    ],
  })
}