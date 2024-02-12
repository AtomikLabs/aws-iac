resource "aws_ecr_repository_policy" "repo_access_policy" {
  repository = aws_ecr_repository.repo.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:GetAuthorizationToken",
        ]
        Resource = "*"
      }
    ]
  })
}