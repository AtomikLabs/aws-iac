resource "aws_ecr_repository_policy" "repo_access_policy" {
  repository = aws_ecr_repository.repo.name

  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Action" : [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ],
        "Resource" : aws_ecr_repository.repo.arn
      }
    ]
  })
}

resource "aws_iam_policy" "ecr_auth_token_policy" {
  name        = "ECRAuthTokenPolicy"
  description = "Policy to allow authentication with ECR."

  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Action" : "ecr:GetAuthorizationToken",
        "Resource" : "*"
      }
    ]
  })
}
