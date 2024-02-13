resource "aws_ecr_repository" "repo" {
  name                 = "${var.ENVIRONMENT_NAME}-repo"
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration {
    scan_on_push = true
  }
  tags = {
    Name = "${var.ENVIRONMENT_NAME}-repo"
  }
}

resource "aws_ecr_lifecycle_policy" "repo_lifecycle_policy" {
  repository = aws_ecr_repository.repo.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1,
        description = "Expire images older than 14 days",
        selection = {
          tagStatus = "untagged",
          countType = "sinceImagePushed",
          countUnit = "days",
          countNumber = 14
        },
        action = {
          type = "expire"
        }
      }
    ]
  })
}