resource "aws_instance" "rabbitmq" {
  count                     = 2
  ami                       = "ami-0c7217cdde317cfec" #ubuntu
  instance_type             = "t2.micro"
  subnet_id                 = aws_subnet.private[count.index].id
  key_name                  = "${local.environment}-${local.bastion_host_key_pair_name}"
  vpc_security_group_ids    = [aws_security_group.rabbitmq_sg.id]

  user_data = <<-EOF
            #!/bin/sh
            {
            echo "Starting RabbitMQ installation"
            sudo apt-get install curl gnupg apt-transport-https -y

            ## Team RabbitMQ's main signing key
            curl -1sLf "https://keys.openpgp.org/vks/v1/by-fingerprint/0A9AF2115F4687BD29803A206B73A36E6026DFCA" | sudo gpg --dearmor | sudo tee /usr/share/keyrings/com.rabbitmq.team.gpg > /dev/null
            ## Community mirror of Cloudsmith: modern Erlang repository
            curl -1sLf https://github.com/rabbitmq/signing-keys/releases/download/3.0/cloudsmith.rabbitmq-erlang.E495BB49CC4BBE5B.key | sudo gpg --dearmor | sudo tee /usr/share/keyrings/rabbitmq.E495BB49CC4BBE5B.gpg > /dev/null
            ## Community mirror of Cloudsmith: RabbitMQ repository
            curl -1sLf https://github.com/rabbitmq/signing-keys/releases/download/3.0/cloudsmith.rabbitmq-server.9F4587F226208342.key | sudo gpg --dearmor | sudo tee /usr/share/keyrings/rabbitmq.9F4587F226208342.gpg > /dev/null

            ## Add apt repositories maintained by Team RabbitMQ
            sudo tee /etc/apt/sources.list.d/rabbitmq.list <<EOF_INNER
            ## Provides modern Erlang/OTP releases
            ##
            deb [signed-by=/usr/share/keyrings/rabbitmq.E495BB49CC4BBE5B.gpg] https://ppa1.novemberain.com/rabbitmq/rabbitmq-erlang/deb/ubuntu jammy main
            deb-src [signed-by=/usr/share/keyrings/rabbitmq.E495BB49CC4BBE5B.gpg] https://ppa1.novemberain.com/rabbitmq/rabbitmq-erlang/deb/ubuntu jammy main

            # another mirror for redundancy
            deb [signed-by=/usr/share/keyrings/rabbitmq.E495BB49CC4BBE5B.gpg] https://ppa2.novemberain.com/rabbitmq/rabbitmq-erlang/deb/ubuntu jammy main
            deb-src [signed-by=/usr/share/keyrings/rabbitmq.E495BB49CC4BBE5B.gpg] https://ppa2.novemberain.com/rabbitmq/rabbitmq-erlang/deb/ubuntu jammy main

            ## Provides RabbitMQ
            ##
            deb [signed-by=/usr/share/keyrings/rabbitmq.9F4587F226208342.gpg] https://ppa1.novemberain.com/rabbitmq/rabbitmq-server/deb/ubuntu jammy main
            deb-src [signed-by=/usr/share/keyrings/rabbitmq.9F4587F226208342.gpg] https://ppa1.novemberain.com/rabbitmq/rabbitmq-server/deb/ubuntu jammy main

            # another mirror for redundancy
            deb [signed-by=/usr/share/keyrings/rabbitmq.9F4587F226208342.gpg] https://ppa2.novemberain.com/rabbitmq/rabbitmq-server/deb/ubuntu jammy main
            deb-src [signed-by=/usr/share/keyrings/rabbitmq.9F4587F226208342.gpg] https://ppa2.novemberain.com/rabbitmq/rabbitmq-server/deb/ubuntu jammy main
            EOF_INNER
            ## Update package indices
            sudo apt-get update -y

            ## Install Erlang packages
            sudo apt-get install -y erlang-base \
            erlang-asn1 erlang-crypto erlang-eldap erlang-ftp erlang-inets \
            erlang-mnesia erlang-os-mon erlang-parsetools erlang-public-key \
            erlang-runtime-tools erlang-snmp erlang-ssl \
            erlang-syntax-tools erlang-tftp erlang-tools erlang-xmerl

            ## Install rabbitmq-server and its dependencies
            sudo apt-get install rabbitmq-server -y --fix-missing

            # Start the RabbitMQ server
            sudo systemctl enable rabbitmq-server
            sudo systemctl start rabbitmq-server
            sudo rabbitmq-plugins enable rabbitmq_management

            sleep 15
            sudo rabbitmqctl add_user ${local.rabbitmqctl_username} ${local.rabbitmqctl_password}
            sudo rabbitmqctl set_user_tags ${local.rabbitmqctl_username} administrator
            sudo rabbitmqctl set_permissions -p / ${local.rabbitmqctl_username} ".*" ".*" ".*"
            } >> /var/log/user-data.log 2>&1
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

  ingress {
    from_port   = 15672
    to_port     = 15672
    protocol    = "tcp"
    security_groups = [aws_security_group.bastion_sg.id]
  }

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    security_groups = [aws_security_group.bastion_sg.id]
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