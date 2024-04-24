locals {
  availability_zone_available_names             = var.availability_zones
  aws_vpc_id                                    = var.aws_vpc_id
  data_ingestion_metadata_key_prefix            = var.data_ingestion_metadata_key_prefix
  default_ami_id                                = var.default_ami_id
  environment                                   = var.environment
  home_ip                                       = var.home_ip
  infra_config_bucket_arn                       = var.infra_config_bucket_arn
  app_name                                      = var.app_name
  orchestration_ami_id                          = var.orchestration_ami_id
  orchestration_instance_type                   = var.orchestration_instance_type
  orchestration_key_pair_name                   = var.orchestration_key_pair_name
  orchestration_resource_prefix                 = var.orchestration_resource_prefix
  orchestration_source_security_group_ids       = var.orchestration_source_security_group_ids
  private_subnets                               = var.private_subnets
  region                                        = var.region
  ssm_policy_for_instances_arn                  = var.ssm_policy_for_instances_arn
  tags                                          = var.tags
}

resource "aws_instance" "orchestration_host" {
  ami = local.orchestration_ami_id
  instance_type = local.orchestration_instance_type
  iam_instance_profile = aws_iam_instance_profile.orchestration_instance_profile.name
  key_name = "${local.environment}-${local.orchestration_key_pair_name}"
  subnet_id = element(local.private_subnets, 0)
  user_data = <<-EOF
#!/bin/bash

sudo yum update -y
yum install docker -y
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user
EOF
  
  vpc_security_group_ids = [ aws_security_group.orchestration_security_group.id ]

  depends_on = [ aws_ebs_volume.orchestration_host_volume ]

  tags = {
    Name = "${local.environment}-orchestration-host"
  }
}

resource "aws_ebs_volume" "orchestration_ebs_volume" {
  availability_zone = local.availability_zone_available_names[0]
  size              = 10

  tags = {
    Name = "${local.environment}-orchestration-data-volume"
    orchestration-backup = "true"
  }

  lifecycle {
    prevent_destroy = true # Essential to prevent accidental deletion of data!
  }
}

resource "aws_volume_attachment" "orchestration_ebs_attachment" {
  device_name = "/dev/sdh"
  volume_id   = aws_ebs_volume.orchestration_ebs_volume.id
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
      }
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
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [local.home_ip]
  }

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    security_groups = local.orchestration_source_security_group_ids
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

resource "aws_iam_role_policy_attachment" "orchestration_role_ssm_policy_for_instances" {
  role       = aws_iam_role.orchestration_instance_role.name
  policy_arn = local.ssm_policy_for_instances_arn
}

resource "aws_iam_instance_profile" "orchestration_instance_profile" {
  name = "${local.environment}-orchestration-instance-profile"
  role = aws_iam_role.orchestration_instance_role.name
}