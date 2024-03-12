data "aws_secretsmanager_secret_version" "neo4j_credentials" {
  secret_id = "${var.environment}/neo4j-credentials"
}

locals {
  availability_zone_available_names             = var.availability_zones
  aws_vpc_id                                    = var.aws_vpc_id
  bastion_host_ip                               = var.bastion_host_ip
  data_ingestion_metadata_key_prefix            = var.data_ingestion_metadata_key_prefix
  default_ami_id                                = var.default_ami_id
  environment                                   = var.environment
  home_ip                                       = var.home_ip
  infra_config_bucket_arn                       = var.infra_config_bucket_arn
  name                                          = var.name
  neo4j_ami_id                                  = var.neo4j_ami_id
  neo4j_instance_type                           = var.neo4j_instance_type
  neo4j_key_pair_name                           = var.neo4j_key_pair_name
  neo4j_resource_prefix                         = var.neo4j_resource_prefix
  private_subnets                               = var.private_subnets
  region                                        = var.region
  secret                                        = jsondecode(data.aws_secretsmanager_secret_version.neo4j_credentials.secret_string)
  ssm_policy_for_instances_arn                  = var.ssm_policy_for_instances_arn
  tags                                          = var.tags
}
resource "aws_s3_bucket" "atomiklabs_data_bucket" {
  bucket = "${local.environment}-${local.name}-data-bucket"  
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

resource "aws_glue_catalog_database" "data_catalog_database" {
  name = "${local.environment}-data_catalog_database"
  tags = local.tags
}

resource "aws_glue_catalog_table" "data_ingestion_metadata_table" {
  database_name = aws_glue_catalog_database.data_catalog_database.name
  name          = "${local.environment}-data_ingestion_metadata_table"
  table_type = "EXTERNAL_TABLE"

  parameters = {
    EXTERNAL              = "TRUE"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://${aws_s3_bucket.atomiklabs_data_bucket.id}/${local.data_ingestion_metadata_key_prefix}/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"
    ser_de_info {
      name                  = "${local.environment}-my_serde"
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "date_time"
      type = "timestamp"
    }
    columns {
      name = "environment"
      type = "string"
    }
    columns {
      name = "app_name"
      type = "string"
    }
    columns {
      name = "function_name"
      type = "string"
    }
    columns {
      name = "uri"
      type = "string"
    }
    columns {
      name = "size_of_data_downloaded"
      type = "bigint"
    }
    columns {
      name = "ingestion_job_uuid"
      type = "string"
    }
    columns {
      name = "status"
      type = "string"
    }
    columns {
      name = "error_message"
      type = "string"
    }
    columns {
      name = "triggered_functions"
      type = "string"
    }
    columns {
      name = "original_data_format"
      type = "string"
    }
    columns {
      name = "stored_data_format"
      type = "string"
    }
    columns {
      name = "data_source"
      type = "string"
    }
    columns {
      name = "raw_data_bucket"
      type = "string"
    }
    columns {
      name = "raw_data_key"
      type = "string"
    }
  }
}

resource "aws_iam_role" "lambda_glue_role" {
  name = "${local.environment}-lambda_glue_access_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "lambda.amazonaws.com"
        },
      },
    ],
  })
  tags = local.tags
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

resource "aws_instance" "neo4j_host" {
  ami = local.neo4j_ami_id
  instance_type = local.neo4j_instance_type
  iam_instance_profile = aws_iam_instance_profile.neo4j_instance_profile.name
  key_name = "${local.environment}-${local.neo4j_key_pair_name}"
  subnet_id = element(local.private_subnets, 0)
  user_data = <<-EOF
#!/bin/bash

yum install docker -y
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

target=$(readlink -f /dev/sdh)
if sudo file -s "$target" | grep -q "ext"; then
  echo "Filesystem exists on target"
else
  /usr/sbin/mkfs.ext4 /dev/sdh
fi

mount /dev/sdh /neo4j
mkdir -p /neo4j/data
mkdir -p /neo4j/logs

chown :docker /neo4j/data /neo4j/logs
chmod g+rwx /neo4j/data /neo4j/logs

docker run --restart=always \
-p 7474:7474 -p 7687:7687 \
-v /neo4j/data:/data \
-v /neo4j/logs:/logs \
-e NEO4J_AUTH=${local.secret.username}/${local.secret.password} \
--name neo4j \
neo4j:latest
EOF

  vpc_security_group_ids = [
    aws_security_group.neo4j_security_group.id
  ]

  depends_on = [ aws_ebs_volume.neo4j_ebs_volume ]

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
    cidr_blocks = ["${local.home_ip}/32", "${local.bastion_host_ip}/32"]
  }

  ingress {
    from_port   = 7473
    to_port     = 7473
    protocol    = "tcp"
    cidr_blocks = ["${local.home_ip}/32", "${local.bastion_host_ip}/32"]
  }

  ingress {
    from_port   = 7474
    to_port     = 7474
    protocol    = "tcp"
    cidr_blocks = ["${local.home_ip}/32", "${local.bastion_host_ip}/32"]
  }

  ingress {
    from_port   = 7687
    to_port     = 7687
    protocol    = "tcp"
    cidr_blocks = ["${local.home_ip}/32", "${local.bastion_host_ip}/32"]
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