resource "aws_instance" "rabbitmq" {
  count                     = 2
  ami                       = "ami-0c7217cdde317cfec" #ubuntu
  instance_type             = "t2.micro"
  subnet_id                 = aws_subnet.private[count.index].id
  key_name                  = "${local.environment}-${local.bastion_host_key_pair_name}"
  vpc_security_group_ids    = [aws_security_group.rabbitmq_sg.id]
  user_data                 = file("../../infra/core/messaging/src/init-instance.sh")
  iam_instance_profile      = aws_iam_instance_profile.rabbitmq_profile.name
  tags = {
    Name = "${local.environment}-RabbitMQ-${count.index + 1}"
    Environment = local.environment
  }
}

resource "aws_iam_role" "rabbitmq_role" {
  name = "${local.environment}-rabbitmq-role"
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

resource "aws_iam_instance_profile" "rabbitmq_profile" {
  name = "${local.environment}-rabbitmq-profile"
  role = aws_iam_role.rabbitmq_role.name
}

resource "aws_iam_role_policy_attachment" "rabbitmq_role_s3_infra_bucket" {
  role       = aws_iam_role.rabbitmq_role.name
  policy_arn = aws_iam_policy.s3_infra_config_bucket_access.arn
}

resource "aws_iam_role_policy_attachment" "rabbitmq_role_ssm_managed_instance" {
  role       = aws_iam_role.rabbitmq_role.name
  policy_arn = local.AmazonSSMManagedInstanceCoreARN
}

resource "aws_security_group" "rabbitmq_sg" {
  name        = "${local.environment}-rabbitmq-sg"
  description = "Security group for RabbitMQ"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    security_groups = [aws_security_group.bastion_sg.id]
  }

  ingress {
    from_port   = 4369
    to_port     = 4369
    protocol    = "tcp"
    self = true
  }

  ingress {
    from_port   = 5672
    to_port     = 5672
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }

  ingress {
    from_port   = 9100
    to_port     = 9100
    protocol    = "tcp"
    cidr_blocks = [for subnet in aws_subnet.private : subnet.cidr_block]
  }

  ingress {
    from_port   = 15672
    to_port     = 15672
    protocol    = "tcp"
    security_groups = [aws_security_group.bastion_sg.id]
  }

  ingress {
    from_port   = 25672
    to_port     = 25672
    protocol    = "tcp"
    self = true
  }


  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.tags
}