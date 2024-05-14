data "aws_secretsmanager_secret_version" "neo4j_credentials" {
  secret_id = "${var.environment}/neo4j-credentials"
}

locals {
  availability_zone_available_names             = var.availability_zones
  aws_vpc_id                                    = var.aws_vpc_id
  data_ingestion_metadata_key_prefix            = var.data_ingestion_metadata_key_prefix
  default_ami_id                                = var.default_ami_id
  environment                                   = var.environment
  home_ip                                       = var.home_ip
  infra_config_bucket_arn                       = var.infra_config_bucket_arn
  app_name                                          = var.app_name
  neo4j_ami_id                                  = var.neo4j_ami_id
  neo4j_instance_type                           = var.neo4j_instance_type
  neo4j_key_pair_name                           = var.neo4j_key_pair_name
  neo4j_resource_prefix                         = var.neo4j_resource_prefix
  neo4j_source_security_group_ids               = var.neo4j_source_security_group_ids
  private_subnets                               = var.private_subnets
  region                                        = var.region
  secret                                        = jsondecode(data.aws_secretsmanager_secret_version.neo4j_credentials.secret_string)
  ssm_policy_for_instances_arn                  = var.ssm_policy_for_instances_arn
  tags                                          = var.tags
}
resource "aws_s3_bucket" "atomiklabs_data_bucket" {
  bucket = "${local.environment}-${local.app_name}-data-bucket"  
  tags = local.tags
}

resource "aws_s3_bucket_lifecycle_configuration" "data_lifecycle" {
  bucket = aws_s3_bucket.atomiklabs_data_bucket.id

  rule {
    id     = "expire-old-metadata"
    status = "Enabled"

    expiration {
      days = 365
    }

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data_encryption" {
  bucket = aws_s3_bucket.atomiklabs_data_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
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
  tags = local.tags
}

data "template_file" "init_script" {
  template = file("${path.module}/init.tpl")

  vars = {
    neo4j_username = local.secret.neo4j_username
    neo4j_password = local.secret.neo4j_password
  }
}

resource "null_resource" "init_trigger" {
  triggers = {
    init_script_hash = filemd5("${path.module}/init.tpl")
  }
}

resource "aws_instance" "neo4j_host" {
  ami = local.neo4j_ami_id
  instance_type = local.neo4j_instance_type
  iam_instance_profile = aws_iam_instance_profile.neo4j_instance_profile.name
  key_name = "${local.environment}-${local.neo4j_key_pair_name}"
  subnet_id = element(local.private_subnets, 0)
  user_data = data.template_file.init_script.rendered

  vpc_security_group_ids = [
    aws_security_group.neo4j_security_group.id
  ]

  depends_on = [ aws_ebs_volume.neo4j_ebs_volume, null_resource.init_trigger ]

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name = "${local.environment}-neo4j-host"
  }
}

resource "aws_ebs_volume" "neo4j_ebs_volume" {
  availability_zone = local.availability_zone_available_names[0]
  size              = 50

  tags = {
    Name = "${local.environment}-neo4j-data-volume"
    neo4j-backup = "true"
  }

  lifecycle {
    prevent_destroy = true # Essential to prevent accidental deletion of data!
  }
}

resource "aws_volume_attachment" "neo4j_ebs_attachment" {
  device_name = "/dev/sdh"
  volume_id   = aws_ebs_volume.neo4j_ebs_volume.id
  instance_id = aws_instance.neo4j_host.id
  skip_destroy = true
}

resource "aws_iam_role" "neo4j_role" {
  name = "${local.environment}-neo4j-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "dlm.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_dlm_lifecycle_policy" "neo4j_ebs_snapshot_policy" {
  description        = "EBS Snapshot Lifecycle Policy"
  execution_role_arn = aws_iam_role.neo4j_role.arn

  policy_details {
    resource_types = ["VOLUME"]

    schedule {
      name = "2AM Daily"
      
      create_rule {
        interval      = 24
        interval_unit = "HOURS"
        times         = ["02:00"]
      }

      retain_rule {
        count = 1
      }

      tags_to_add = {
        "SnapshotCreator" = "DLM"
      }

      copy_tags = false
    }

    target_tags = {
      "neo4j-backup" = "true"
    }
  }
  
  state = "ENABLED"
}

resource "aws_security_group" "neo4j_security_group" {
  name_prefix = "${local.environment}-neo4j-sg"
  vpc_id      = local.aws_vpc_id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [local.home_ip]
  }

  ingress {
    from_port   = 7473
    to_port     = 7473
    protocol    = "tcp"
    cidr_blocks = [local.home_ip]
  }

  ingress {
    from_port   = 7474
    to_port     = 7474
    protocol    = "tcp"
    cidr_blocks = [local.home_ip]
  }

  ingress {
    from_port   = 7687
    to_port     = 7687
    protocol    = "tcp"
    cidr_blocks = [local.home_ip]
  }

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    security_groups = local.neo4j_source_security_group_ids
  }

  ingress {
    from_port   = 7473
    to_port     = 7473
    protocol    = "tcp"
    security_groups = local.neo4j_source_security_group_ids
  }

  ingress {
    from_port   = 7474
    to_port     = 7474
    protocol    = "tcp"
    security_groups = local.neo4j_source_security_group_ids
  }

  ingress {
    from_port   = 7687
    to_port     = 7687
    protocol    = "tcp"
    security_groups = local.neo4j_source_security_group_ids
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    local.tags,
    {
      "Name" = "${local.environment}-neo4j-sg"
    }
  )
}

resource "aws_iam_role" "neo4j_instance_role" {
  name = "${local.environment}-neo4j-instance-role"
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

resource "aws_iam_role_policy_attachment" "neo4j_role_ssm_policy_for_instances" {
  role       = aws_iam_role.neo4j_instance_role.name
  policy_arn = local.ssm_policy_for_instances_arn
}

resource "aws_iam_instance_profile" "neo4j_instance_profile" {
  name = "${local.environment}-neo4j-instance-profile"
  role = aws_iam_role.neo4j_instance_role.name
}