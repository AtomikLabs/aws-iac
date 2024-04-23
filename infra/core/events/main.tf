locals {
    data_bucket                     = var.data_bucket
    data_bucket_arn                 = var.data_bucket_arn
    data_ingestion_key_prefix       = var.data_ingestion_key_prefix
    environment                     = var.environment
    etl_key_prefix                  = var.etl_key_prefix
    parse_arxiv_summaries_name      = var.parse_arxiv_summaries_name
    parse_arxiv_summaries_arn       = var.parse_arxiv_summaries_arn
    store_arxiv_summaries_name      = var.store_arxiv_summaries_name
    store_arxiv_summaries_arn       = var.store_arxiv_summaries_arn
    persist_arxiv_summaries_name    = var.persist_arxiv_summaries_name
    persist_arxiv_summaries_arn     = var.persist_arxiv_summaries_arn
}

resource "aws_s3_bucket_notification" "dev_data_bucket_triggerss" {
  bucket = local.data_bucket

  lambda_function {
    id = "${local.environment}-${local.parse_arxiv_summaries_name}-s3-trigger"
    lambda_function_arn = "${local.parse_arxiv_summaries_arn}"
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = local.data_ingestion_key_prefix
    filter_suffix       = ".json"
  }

  lambda_function {
    id = "${local.environment}-${local.store_arxiv_summaries_name}-s3-trigger"
    lambda_function_arn = "${local.store_arxiv_summaries_arn}"
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = local.etl_key_prefix
    filter_suffix       = ".json"
  }

  lambda_function {
    id = "${local.environment}-${local.persist_arxiv_summaries_name}-s3-trigger"
    lambda_function_arn = "${local.persist_arxiv_summaries_arn}"
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = local.etl_key_prefix
    filter_suffix       = ".json"
  }

  depends_on = [
    aws_lambda_permission.allow_s3_bucket_parse_arxiv_summaries,
    aws_lambda_permission.allow_s3_bucket_store_arxiv_summaries,
    aws_lambda_permission.allow_s3_bucket_persist_arxiv_summaries,
  ]
}


resource "aws_lambda_permission" "allow_s3_bucket_parse_arxiv_summaries" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = local.parse_arxiv_summaries_name
  principal     = "s3.amazonaws.com"
  source_arn    = "${local.data_bucket_arn}"
}

resource "aws_lambda_permission" "allow_s3_bucket_store_arxiv_summaries" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = local.store_arxiv_summaries_name
  principal     = "s3.amazonaws.com"
  source_arn    = "${local.data_bucket_arn}"
}

resource "aws_lambda_permission" "allow_s3_bucket_persist_arxiv_summaries" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = local.persist_arxiv_summaries_name
  principal     = "s3.amazonaws.com"
  source_arn    = "${local.data_bucket_arn}"
}

