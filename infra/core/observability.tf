resource "aws_instance" "observer" {
  ami = "ami-0c7217cdde317cfec" # ubuntu
  count = 1
  instance_type = "t2.small"
  key_name = "${local.environment}-${local.bastion_host_key_pair_name}"
  subnet_id = aws_subnet.private[0].id
  tags = {
    Name = "observability"
    Environment = local.environment
  }
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
    from_port   = 3000 # Grafana
    to_port     = 3000
    protocol    = "tcp"
    security_groups = []
  }
  
  ingress {
    from_port   = 3100 # Loki
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
    from_port   = 9090 # Prometheus
    to_port     = 9090
    protocol    = "tcp"
    security_groups = []
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.tags
}