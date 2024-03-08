resource "aws_iam_role_policy_attachment" "bastion_host_role_s3_infra_bucket" {
  role       = aws_iam_role.bastion_host_role.name
  policy_arn = aws_iam_policy.s3_infra_config_bucket_access.arn
}

resource "aws_iam_role_policy_attachment" "bastion_role_ssm_managed_instance" {
  role       = aws_iam_role.bastion_host_role.name
  policy_arn = local.AmazonSSMManagedInstanceCoreARN
}

resource "aws_iam_instance_profile" "bastion_host_profile" {
  name = "${local.environment}-bastion-host-profile"
  role = aws_iam_role.bastion_host_role.name
}

resource "aws_iam_role_policy_attachment" "bastion_role_ssm_policy_for_instances" {
  role       = aws_iam_role.bastion_host_role.name
  policy_arn = aws_iam_policy.ssm_policy_for_instances.arn
}

resource "aws_instance" "bastion_host" {
  ami                   = "ami-0440d3b780d96b29d" # ec2
  instance_type         = "t2.micro"
  subnet_id             = element(aws_subnet.public.*.id, 0)
  key_name              = "${local.environment}-${local.bastion_host_key_pair_name}"
  user_data             = file("../../infra/core/networking/src/init-instance.sh")
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
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [local.home_ip]
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

  tags = {
    Name        = "${local.environment}-bastion-sg"
    Environment = local.environment
  }
}
