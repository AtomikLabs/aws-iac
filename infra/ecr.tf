resource "aws_ecr_repository" "repo" {
  name                 = "${local.environment}-repository"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_iam_policy" "ecr_policy" {
  name        = "${local.environment}-ECRPolicy"
  path        = "/"
  description = "ECR policy for pushing and pulling images"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ]
        Resource = "${aws_ecr_repository.repo.arn}"
      },
      {
        Effect = "Allow"
        Action = "ecr:DescribeRepositories"
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role" "ecr_role" {
  name = "${local.environment}-ECRRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_policy_attachment" "ecr_policy_attach" {
  name       = "${local.environment}-ECRPolicyAttachment"
  roles      = [aws_iam_role.ecr_role.name]
  policy_arn = aws_iam_policy.ecr_policy.arn
}

resource "aws_iam_user_policy_attachment" "ecr_user_policy_attach" {
  user       = local.iam_user_name
  policy_arn = aws_iam_policy.ecr_policy.arn
}
