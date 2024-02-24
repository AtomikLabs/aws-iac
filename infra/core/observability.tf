resource "aws_instance" "observer" {
  ami = "ami-0c7217cdde317cfec" # ubuntu
  instance_type = "t2.small"
  key_name = "${local.environment}-${local.bastion_host_key_pair_name}"
  subnet_id = aws_subnet.private[0].id
  user_data = <<-EOF
              #!/bin/bash
              # Update the instance
              apt-get update && apt-get upgrade -y
              # Install Docker
              apt-get install -y apt-transport-https ca-certificates curl software-properties-common
              curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
              add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
              apt-get update
              apt-get install -y docker-ce
              # Install Docker Compose
              curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
              chmod +x /usr/local/bin/docker-compose
              EOF
  tags = {
    Name = "${local.environment}-observability"
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