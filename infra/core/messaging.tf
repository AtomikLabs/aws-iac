resource "aws_instance" "rabbitmq" {
  count                     = 2
  ami                       = "ami-0440d3b780d96b29d"
  instance_type             = "t2.micro"
  subnet_id                 = aws_subnet.private[count.index].id
  key_name                  = "${local.environment}-${local.bastion_host_key_pair_name}"
  vpc_security_group_ids    = [aws_security_group.rabbitmq_sg.id]

  user_data = <<-EOF
              #!/bin/bash
              sudo apt-get update
              sudo apt-get install -y rabbitmq-server
              sudo systemctl enable rabbitmq-server
              sudo systemctl start rabbitmq-server
              EOF

  tags = {
    Name = "RabbitMQ-${count.index + 1}"
    Environment = local.environment
  }
}

resource "aws_security_group" "rabbitmq_sg" {
  name        = "${local.environment}-rabbitmq-sg"
  description = "Security group for RabbitMQ"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 5672
    to_port     = 5672
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${local.environment}-rabbitmq-sg"
    Environment = local.environment
  }
}