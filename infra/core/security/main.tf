locals {
  AmazonSSMManagedInstanceCoreARN     = var.aws_ssm_managed_instance_core_arn
  bastion_ami_id                      = var.bastion_ami_id
  bastion_host_key_pair_name          = var.bastion_host_key_pair_name
  bastion_instance_type               = var.bastion_instance_type
  environment                         = var.environment
  home_ip                             = var.home_ip
  public_subnets                      = var.public_subnets
  vpc_id                              = var.vpc_id
}

resource "aws_iam_role_policy_attachment" "bastion_role_ssm_managed_instance" {
  role       = aws_iam_role.bastion_host_role.name
  policy_arn = local.AmazonSSMManagedInstanceCoreARN
}

resource "aws_iam_instance_profile" "bastion_host_profile" {
  name = "${local.environment}-bastion-host-profile"
  role = aws_iam_role.bastion_host_role.name
}

resource "aws_instance" "bastion_host" {
  ami                   = var.bastion_ami_id
  instance_type         = var.bastion_instance_type
  subnet_id             = element(local.public_subnets, 0)
  key_name              = "${local.environment}-${local.bastion_host_key_pair_name}"
  iam_instance_profile  = aws_iam_instance_profile.bastion_host_profile.name

  vpc_security_group_ids = [
    aws_security_group.bastion_sg.id,
  ]

  tags = {
    Name        = "${local.environment}-bastion-host"
    Environment = local.environment
  }
}

resource "aws_iam_role" "bastion_host_role" {
  name = "${local.environment}-bastion-host-role"
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

resource "aws_security_group" "bastion_sg" {
  name        = "${local.environment}-bastion-sg"
  description = "Security group for Bastion Host"
  vpc_id      = local.vpc_id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [local.home_ip]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${local.environment}-bastion-sg"
    Environment = local.environment
  }
}
