# **********************************************************
# * SERVICE                                                *
# **********************************************************
resource "aws_security_group" "lambda_sg" {
  name        = "${local.environment}-lambda-sg"
  description = "Security group for most app lambdas"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    security_groups = [aws_security_group.bastion_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}