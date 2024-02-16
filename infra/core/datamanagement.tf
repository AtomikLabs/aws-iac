resource "aws_s3_bucket" "data_bucket" {
  bucket = "${local.environment}-data-bucket"
}