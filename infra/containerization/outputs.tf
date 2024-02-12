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
