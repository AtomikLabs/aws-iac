locals {
  account_id                                    = var.account_id
  app_name                                      = var.app_name
  availability_zone_available_names             = var.availability_zones
  arxiv_api_max_retries                         = var.arxiv_api_max_retries
  arxiv_base_url                                = var.arxiv_base_url
  arxiv_sets                                    = var.arxiv_sets
  aws_vpc_id                                    = var.aws_vpc_id
  bastion_host_security_group_id                = var.bastion_host_security_group_id
  data_bucket                                   = var.data_bucket
  data_bucket_arn                               = var.data_bucket_arn
  default_ami_id                                = var.default_ami_id
  environment                                   = var.environment
  home_ip                                       = var.home_ip
  infra_config_bucket                           = var.infra_config_bucket
  infra_config_bucket_arn                       = var.infra_config_bucket_arn
  neo4j_username                                = var.neo4j_username
  neo4j_password                                = var.neo4j_password
  orchestration_ami_id                          = var.orchestration_ami_id
  orchestration_host_volume_name                = "${var.environment}-${var.orchestration_resource_prefix}-data-volume"
  orchestration_instance_type                   = var.orchestration_instance_type
  orchestration_key_pair_name                   = var.orchestration_key_pair_name
  orchestration_resource_prefix                 = var.orchestration_resource_prefix
  orchestration_source_security_group_ids       = var.orchestration_source_security_group_ids
  pods_prefix                                    = var.pods_prefix
  private_subnets                               = var.private_subnets
  region                                        = var.region
  ssm_policy_for_instances_arn                  = var.ssm_policy_for_instances_arn
  tags                                          = var.tags
}

# **********************************************************
# * ORCHESTRATION HOST                                     *
# **********************************************************

data "template_file" "init_script" {
  template = file("${path.module}/init.tpl")

  vars = {
    environment = local.environment
    bucket_name = local.data_bucket
    infra_bucket_name = local.infra_config_bucket
    neo4j_username = local.neo4j_username
    neo4j_password = local.neo4j_password
    volume_name_tag = local.orchestration_host_volume_name
  }
}

resource "null_resource" "init_trigger" {
  triggers = {
    init_script_hash = filemd5("${path.module}/init.tpl")
  }
}

resource "aws_instance" "orchestration_host" {
  ami = local.orchestration_ami_id
  instance_type = local.orchestration_instance_type
  iam_instance_profile = aws_iam_instance_profile.orchestration_instance_profile.name
  key_name = "${local.environment}-${local.orchestration_key_pair_name}"
  subnet_id = element(local.private_subnets, 0)
  user_data = data.template_file.init_script.rendered
  
  vpc_security_group_ids = [ aws_security_group.orchestration_security_group.id ]

  depends_on = [ aws_ebs_volume.orchestration_host_volume, null_resource.init_trigger ]

   lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name = "${local.environment}-orchestration-host"
  }

}

resource "aws_ebs_volume" "orchestration_host_volume" {
  availability_zone = local.availability_zone_available_names[0]
  size              = 15

  tags = {
    Name = local.orchestration_host_volume_name
    orchestration-backup = "true"
  }

  lifecycle {
    prevent_destroy = true # Essential to prevent accidental deletion of data!
  }
}

resource "aws_volume_attachment" "orchestration_ebs_attachment" {
  device_name = "/dev/sdh"
  volume_id   = aws_ebs_volume.orchestration_host_volume.id
  instance_id = aws_instance.orchestration_host.id
}

resource "aws_iam_role" "orchestration_role" {
  name = "${local.environment}-orchestration-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "dlm.amazonaws.com"
        }
      },
    ]
  })
}

resource "aws_dlm_lifecycle_policy" "orchestration_ebs_snapshot_policy" {
  description        = "EBS Snapshot Lifecycle Policy"
  execution_role_arn = aws_iam_role.orchestration_role.arn

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
      "orchestration-backup" = "true"
    }
  }
  
  state = "ENABLED"
}

resource "aws_security_group" "orchestration_security_group" {
  name_prefix = "${local.environment}-orchestration-sg"
  vpc_id      = local.aws_vpc_id

  ingress {
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    security_groups = [local.bastion_host_security_group_id]
  }

  # Flower
  ingress {
    from_port       = 5555
    to_port         = 5555
    protocol        = "tcp"
    security_groups = [local.bastion_host_security_group_id]
  }

  ingress {
    from_port = 5555
    to_port = 5555
    protocol = "tcp"
    self = true
  }

  ingress {
    from_port = 7473
    to_port = 7473
    protocol = "tcp"
    security_groups = [local.bastion_host_security_group_id]
  }

  ingress {
    from_port = 7473
    to_port = 7473
    protocol = "tcp"
    self = true
  }

  ingress {
    from_port = 7474
    to_port = 7474
    protocol = "tcp"
    security_groups = [local.bastion_host_security_group_id]
  }

  ingress {
    from_port = 7474
    to_port = 7474
    protocol = "tcp"
    self = true
  }

  ingress {
    from_port = 7687
    to_port = 7687
    protocol = "tcp"
    security_groups = [local.bastion_host_security_group_id]
  }

  ingress {
    from_port = 7687
    to_port = 7687
    protocol = "tcp"
    self = true
  }

  # Kafka-UI
  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [local.bastion_host_security_group_id]
  }

  # Airflow UI
  ingress {
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [local.bastion_host_security_group_id]
  }

  # Kafka Clients
  ingress {
    from_port       = 9092
    to_port         = 9092
    protocol        = "tcp"
    security_groups = local.orchestration_source_security_group_ids
  }

  ingress {
    from_port       = 9092
    to_port         = 9092
    protocol        = "tcp"
    self            = true
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
      "Name" = "${local.environment}-orchestration-sg"
    }
  )
}

resource "aws_iam_role" "orchestration_instance_role" {
  name = "${local.environment}-orchestration-instance-role"
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

resource "aws_iam_policy" "orchestration_ec2_s3_access" {
  name        = "${local.environment}-${local.orchestration_resource_prefix}-ec2-s3-access"
  description = "Allow ec2 to put objects in S3"

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
          "${local.data_bucket_arn}/*",
          "${local.infra_config_bucket_arn}/${local.orchestration_resource_prefix}/*",
          "${local.infra_config_bucket_arn}/${local.pods_prefix}/*",
        ]
      },
      {
        Action = [
          "s3:ListBucket"
        ]
        Effect = "Allow",
        Resource = [
          "${local.data_bucket_arn}",
          "${local.infra_config_bucket_arn}"
        ]
      }
    ]
  })
}

resource "aws_iam_policy" "orchestration_ebs_policy" {
  name        = "${local.environment}-${local.orchestration_resource_prefix}-ebs-policy"
  description = "Allow ec2 to list EBS volumes"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "ec2:DescribeVolumes",
        ]
        Effect = "Allow",
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_policy" "orchestration_secrets_policy" {
  name        = "${local.environment}-${local.orchestration_resource_prefix}-secrets-policy"
  description = "Allow ec2 to get secrets from Secrets Manager"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "secretsmanager:GetSecretValue",
        ]
        Effect = "Allow",
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_policy" "orchestration_glue_policy" {
  name        = "${var.environment}-airflow-glue-access"
  description = "IAM policy for Airflow EC2 to access Glue Schema Registry"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "glue:GetSchemaVersion",
          "glue:GetSchemaVersionsDiff",
          "glue:GetSchemaByDefinition",
          "glue:RegisterSchemaVersion",
          "glue:PutSchemaVersionMetadata",
          "glue:DeleteSchemaVersions",
          "glue:UpdateSchema"
        ]
        Resource = [
          "arn:aws:glue:${local.region}:${local.account_id}:registry/${aws_glue_registry.glue_registry.registry_name}",
          "arn:aws:glue:${local.region}:${local.account_id}:schema/${aws_glue_registry.glue_registry.registry_name}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_policy" "orchestration_polly_policy" {
  name = "${local.environment}-${local.orchestration_resource_prefix}-polly-policy"
  description = "Allow ec2 to call Polly"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "polly:GetSpeechSynthesisTask",
          "polly:ListSpeechSynthesisTasks",
          "polly:StartSpeechSynthesisTask",
          "polly:SynthesizeSpeech"
        ]
        Effect = "Allow",
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "orchestration_role_ssm_policy_for_instances" {
  role       = aws_iam_role.orchestration_instance_role.name
  policy_arn = local.ssm_policy_for_instances_arn
}

resource "aws_iam_instance_profile" "orchestration_instance_profile" {
  name = "${local.environment}-orchestration-instance-profile"
  role = aws_iam_role.orchestration_instance_role.name
}

resource "aws_iam_role_policy_attachment" "orchestration_role_ec2_s3_access" {
  role       = aws_iam_role.orchestration_instance_role.name
  policy_arn = aws_iam_policy.orchestration_ec2_s3_access.arn
}

resource "aws_iam_role_policy_attachment" "orchestration_role_ebs_policy" {
  role       = aws_iam_role.orchestration_instance_role.name
  policy_arn = aws_iam_policy.orchestration_ebs_policy.arn
}

resource "aws_iam_role_policy_attachment" "orchestration_role_secrets_policy" {
  role       = aws_iam_role.orchestration_instance_role.name
  policy_arn = aws_iam_policy.orchestration_secrets_policy.arn
}

resource "aws_iam_role_policy_attachment" "orchestration_role_glue_policy" {
  role       = aws_iam_role.orchestration_instance_role.name
  policy_arn = aws_iam_policy.orchestration_glue_policy.arn
}

resource "aws_iam_role_policy_attachment" "orchestration_role_polly_policy" {
  role       = aws_iam_role.orchestration_instance_role.name
  policy_arn = aws_iam_policy.orchestration_polly_policy.arn
}

# **********************************************************
# * SCHEMAS AND REGISTRY                                   *
# **********************************************************

resource "aws_glue_registry" "glue_registry" {
    registry_name = "${local.environment}-glue-registry"
}

resource "aws_glue_schema" "arxiv_research_ingestion_event_schema" {
    schema_name = "${local.environment}_arxiv_research_ingestion_event_schema"
    compatibility = "NONE"
    data_format = "AVRO"
    registry_arn = aws_glue_registry.glue_registry.arn
    schema_definition = file("${path.module}/schemas/arxiv_research_ingestion_event_schema.avsc")
}
