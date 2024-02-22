output "data_bucket_id" {
  value = aws_s3_bucket.atomiklabs_data_bucket.id
}

output "data_bucket_name" {
  value = aws_s3_bucket.atomiklabs_data_bucket.bucket
}

output "data_bucket_arn" {
  value = aws_s3_bucket.atomiklabs_data_bucket.arn
}

output "aws_glue_catalog_database_id" {
  value = aws_glue_catalog_database.data_catalog_database.id
}

output "aws_glue_catalog_database_name" {
  value = aws_glue_catalog_database.data_catalog_database.name
}

output "data_ingestion_metadata_table_id" {
  value = aws_glue_catalog_table.data_ingestion_metadata_table.id
}

output "data_ingestion_metadata_table_name" {
  value = aws_glue_catalog_table.data_ingestion_metadata_table.name
}

output "lambda_glue_role_arn" {
  value = aws_iam_role.lambda_glue_role.arn
}

output "lambda_glue_role_id" {
  value = aws_iam_role.lambda_glue_role.id
}

output "lambda_glue_role_name" {
  value = aws_iam_role.lambda_glue_role.name
}

output "lambda_glue_policy_arn" {
  value = aws_iam_policy.lambda_glue_policy.arn
}

