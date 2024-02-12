resource "aws_eks_cluster" "cluster" {
  name     = "${var.ENVIRONMENT_NAME}-cluster"
  role_arn = aws_iam_role.eks_cluster_role.arn

  vpc_config {
    subnet_ids = concat(var.PUBLIC_SUBNET_IDS, var.PRIVATE_SUBNET_IDS)
    security_group_ids = [var.SECURITY_GROUP_ID]
  }

  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy,
    aws_iam_role_policy_attachment.eks_vpc_resource_controller,
  ]
}

resource "aws_eks_node_group" "general_node_group" {
  cluster_name    = aws_eks_cluster.cluster.name
  node_group_name = "${var.ENVIRONMENT_NAME}-general-node-group"
  node_role_arn   = aws_iam_role.eks_node_role.arn
  subnet_ids      = var.PRIVATE_SUBNET_IDS

  scaling_config {
    desired_size = 1
    max_size     = 2
    min_size     = 1
  }

  depends_on = [aws_eks_cluster.cluster]
}

resource "aws_eks_fargate_profile" "app_fargate_profile" {
  cluster_name           = aws_eks_cluster.cluster.name
  fargate_profile_name   = "${var.ENVIRONMENT_NAME}-fargate-profile"
  pod_execution_role_arn = aws_iam_role.fargate_pod_execution_role.arn
  subnet_ids             = var.PRIVATE_SUBNET_IDS

  selector {
    namespace = "app"
  }
}
