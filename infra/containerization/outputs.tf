output "cluster_endpoint" {
  value       = aws_eks_cluster.cluster.endpoint
  description = "The endpoint for your EKS Kubernetes API. Use this to connect to the cluster."
}

output "cluster_certificate_authority_data" {
  value       = aws_eks_cluster.cluster.certificate_authority[0].data
  description = "The base64 encoded certificate data required to communicate with your EKS cluster."
}

output "cluster_name" {
  value       = aws_eks_cluster.cluster.name
  description = "The name of the EKS cluster."
}

output "node_group_ids" {
  value = aws_eks_node_group.general_node_group.*.id
  description = "The IDs of the EKS node group(s)."
}

output "eks_security_group_id" {
  value       = aws_security_group.eks_sg.id
  description = "The ID of the security group used by the EKS cluster."
}

output "fargate_profile_id" {
  value       = aws_eks_fargate_profile.app_fargate_profile.id
  description = "The ID of the Fargate profile."
}

output "fargate_profile_arn" {
  value       = aws_eks_fargate_profile.app_fargate_profile.arn
  description = "The Amazon Resource Name (ARN) of the Fargate profile."
}

output "fargate_profile_name" {
  value       = aws_eks_fargate_profile.app_fargate_profile.fargate_profile_name
  description = "The name of the Fargate profile."
}

output "fargate_profile_pod_execution_role_arn" {
  value       = aws_eks_fargate_profile.app_fargate_profile.pod_execution_role_arn
  description = "The ARN of the IAM role that provides permissions for the Fargate profile."
}

output "fargate_profile_subnet_ids" {
  value       = aws_eks_fargate_profile.app_fargate_profile.subnet_ids
  description = "The IDs of the subnets associated with the Fargate profile."
}

output "fargate_profile_selector" {
  value = aws_eks_fargate_profile.app_fargate_profile.selector
  description = "The selector to match for pods to use the Fargate profile."
}

output "fargate_profile_cluster_name" {
  value       = aws_eks_fargate_profile.app_fargate_profile.cluster_name
  description = "The name of the EKS cluster."
}

output "general_node_group_id" {
  value       = aws_eks_node_group.general_node_group.id
  description = "The ID of the EKS node group."
}

output "general_node_group_arn" {
  value       = aws_eks_node_group.general_node_group.arn
  description = "The Amazon Resource Name (ARN) of the EKS node group."
}

output "general_node_group_cluster_name" {
  value       = aws_eks_node_group.general_node_group.cluster_name
  description = "The name of the EKS cluster."
}

output "ecr_repository_id" {
  value       = aws_ecr_repository.repo.id
  description = "The ID of the ECR repository."
}

output "ecr_repository_name" {
  value       = aws_ecr_repository.repo.name
  description = "The name of the ECR repository."
}

output "ecr_repository_url" {
  value       = aws_ecr_repository.repo.repository_url
  description = "The URL of the ECR repository."
}
