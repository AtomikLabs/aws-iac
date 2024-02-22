resource "aws_s3_bucket" "atomiklabs_data_bucket" {
  bucket = "${var.environment}-${var.app_name}-data-bucket"
  
  
  tags = var.tags
}

resource "aws_s3_bucket_lifecycle_configuration" "data_lifecycle" {
  bucket = aws_s3_bucket.atomiklabs_data_bucket.id

  rule {
    id     = "expire-old-metadata"
    status = "Enabled"

    expiration {
      days = 365
    }

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data_encryption" {
  bucket = aws_s3_bucket.atomiklabs_data_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_glue_catalog_database" "data_catalog_database" {
  name = "${var.environment}-data_catalog_database"
}

resource "aws_glue_catalog_table" "data_ingestion_metadata_table" {
  database_name = aws_glue_catalog_database.data_catalog_database.name
  name          = "${var.environment}-data_ingestion_metadata_table"

  table_type = "EXTERNAL_TABLE"

  parameters = {
    EXTERNAL              = "TRUE"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://${aws_s3_bucket.atomiklabs_data_bucket.id}/${var.data_ingestion_metadata_key_prefix}/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"
    ser_de_info {
      name                  = "${var.environment}-my_serde"
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "date_time"
      type = "timestamp"
    }
    columns {
      name = "environment"
      type = "string"
    }
    columns {
      name = "app_name"
      type = "string"
    }
    columns {
      name = "function_name"
      type = "string"
    }
    columns {
      name = "uri"
      type = "string"
    }
    columns {
      name = "size_of_data_downloaded"
      type = "bigint"
    }
    columns {
      name = "ingestion_job_uuid"
      type = "string"
    }
    columns {
      name = "status"
      type = "string"
    }
    columns {
      name = "error_message"
      type = "string"
    }
    columns {
      name = "triggered_functions"
      type = "string"
    }
    columns {
      name = "original_data_format"
      type = "string"
    }
    columns {
      name = "stored_data_format"
      type = "string"
    }
    columns {
      name = "data_source"
      type = "string"
    }
    columns {
      name = "raw_data_bucket"
      type = "string"
    }
    columns {
      name = "raw_data_key"
      type = "string"
    }
  }
}

resource "aws_iam_role" "lambda_glue_role" {
  name = "${var.environment}-lambda_glue_access_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "lambda.amazonaws.com"
        },
      },
    ],
  })
}

resource "aws_iam_policy" "lambda_glue_policy" {
  name        = "${var.environment}-lambda_glue_data_catalog_access_policy"
  description = "IAM policy for accessing AWS Glue Data Catalog from Lambda"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = [
          "glue:GetDatabase",
          "glue:GetDatabases",
          "glue:GetTable",
          "glue:GetTables",
          "glue:SearchTables",
          "glue:GetPartitions",
          "glue:GetPartition",
          "glue:StartCrawler",
          "glue:UpdateTable",
          "glue:CreateTable",
        ],
        Effect   = "Allow",
        Resource = "*"
      },
    ],
  })
}

resource "aws_iam_role_policy_attachment" "lambda_glue_policy_attachment" {
  policy_arn = aws_iam_policy.lambda_glue_policy.arn
  role       = aws_iam_role.lambda_glue_role.name
}