resource "aws_instance" "observer" {
  ami = "ami-0c7217cdde317cfec" # ubuntu
  instance_type = "t2.small"
  key_name = "${local.environment}-${local.bastion_host_key_pair_name}"
  subnet_id = aws_subnet.private[0].id
  user_data = file("../../infra/observability/prometheus/src/init-instance.sh")
  iam_instance_profile = aws_iam_instance_profile.observer_profile.name
  tags = {
    Name = "${local.environment}-observability"
    Environment = local.environment
  }
  vpc_security_group_ids = [
    aws_security_group.observer_sg.id
  ]
}

resource "aws_security_group" "observer_sg" {
  name        = "${local.environment}-observer-sg"
  description = "Security group for observability"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    security_groups = [aws_security_group.bastion_sg.id]
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    security_groups = [aws_security_group.bastion_sg.id]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    security_groups = [aws_security_group.bastion_sg.id]
  }

  ingress {
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    security_groups = []
  }
  
  ingress {
    from_port   = 3100
    to_port     = 3100
    protocol    = "tcp"
    security_groups = [
        aws_security_group.bastion_sg.id,
        aws_security_group.lambda_sg.id,
        aws_security_group.rabbitmq_sg.id,
        aws_security_group.rds_sg.id,
        aws_security_group.web_sg.id
    ]
  }

  ingress {
    from_port   = 9090
    to_port     = 9090
    protocol    = "tcp"
    security_groups = []
  }

  ingress {
    from_port   = 9100
    to_port     = 9100
    protocol    = "tcp"
    cidr_blocks = [for subnet in aws_subnet.private : subnet.cidr_block]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.tags
}

resource "aws_iam_role" "observer_role" {
  name = "${local.environment}-observer-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      },
    ]
  })
}

resource "aws_iam_instance_profile" "observer_profile" {
  name = "${local.environment}-observer-profile"
  role = aws_iam_role.observer_role.name
}

resource "aws_iam_role_policy_attachment" "observer_role_s3_infra_bucket" {
  role       = aws_iam_role.observer_role.name
  policy_arn = aws_iam_policy.s3_infra_config_bucket_access.arn
}

resource "aws_iam_role_policy_attachment" "observer_role_ssm_managed_instance" {
  role       = aws_iam_role.observer_role.name
  policy_arn = local.AmazonSSMManagedInstanceCoreARN
}
