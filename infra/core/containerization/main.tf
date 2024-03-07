locals {
  environment = var.environment
}

resource "aws_ecr_repository" "repo" {
  name                 = "${local.environment}-repository"
  image_tag_mutability = "IMMUTABLE"
}
