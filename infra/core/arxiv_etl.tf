# **********************************************************
# * AWS Glue Job                                           *
# **********************************************************
resource "aws_glue_job" "arxiv_xml_to_parquet" {
    name = "${local.environment}-arxiv-to-parquet"
    role_arn = aws_iam_role.glue_service_role.arn
    command {
        script_location="s3://${aws_s3_bucket.atomiklabs_data_bucket.bucket}/${local.etl_key_prefix}/scripts/arxiv_xml_to_parquet.py"
        name = "arxiv_xml_to_parquet"
        python_version = "3"
    }
    default_arguments = {
    "--enable-continuous-cloudwatch-log" = "true"
    "--enable-continuous-log-filter"     = "true"
    "--enable-metrics"                   = "true"
    "--continuous-log-logGroup"          = "/aws-glue/jobs/logs-v2"
  }
}

resource "aws_iam_role" "glue_service_role" {
  name = "${local.environment}-glue-service-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "glue.amazonaws.com"
        },
      },
    ],
  })
}

resource "aws_iam_role_policy_attachment" "glue_service_role_attach" {
  role       = aws_iam_role.glue_service_role.name
  policy_arn = local.AWSGlueServiceRoleARN
}

resource "aws_iam_policy" "glue_s3_access_policy" {
  name   = "${local.environment}-glue-s3-access-policy"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ],
        Effect = "Allow",
        Resource = [
          "${aws_s3_bucket.atomiklabs_data_bucket.arn}/raw_data/data_ingestion/*",
          "${aws_s3_bucket.atomiklabs_data_bucket.arn}/metadata/*"
        ],
      },
    ],
  })
}

resource "aws_iam_role_policy_attachment" "glue_s3_access_policy_attach" {
  role       = aws_iam_role.glue_service_role.name
  policy_arn = aws_iam_policy.glue_s3_access_policy.arn
}

resource "aws_iam_policy" "glue_cloudwatch_policy" {
  name   = "${local.environment}-glue-cloudwatch-policy"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Effect = "Allow",
        Resource = "arn:aws:logs:${local.aws_region}:${local.account_id}:log-group:/aws-glue/jobs/*"
      },
    ],
  })
}

resource "aws_iam_role_policy_attachment" "glue_cloudwatch_policy_attach" {
  role       = aws_iam_role.glue_service_role.name
  policy_arn = aws_iam_policy.glue_cloudwatch_policy.arn
}

resource "aws_sns_topic" "glue_job_failure_notifications" {
  name = "${local.environment}-glue-job-failure-notifications"
}

resource "aws_sns_topic_subscription" "email_subscription" {
  topic_arn = aws_sns_topic.glue_job_failure_notifications.arn
  protocol  = "email"
  endpoint  = "${local.alert_email}"
}

resource "aws_cloudwatch_log_metric_filter" "glue_job_failure_filter" {
  name           = "${local.environment}-glue-job-failure-filter"
  log_group_name = "/aws-glue/jobs"
  pattern        = "\"Job run failed\""

  metric_transformation {
    name      = "GlueJobFailures"
    namespace = "GlueJob"
    value     = "1"
  }
}

resource "aws_cloudwatch_metric_alarm" "glue_job_failure_alarm" {
  alarm_name          = "${local.environment}-glue-job-failure-alarm"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = "1"
  metric_name         = "GlueJobFailures"
  namespace           = "GlueJob"
  period              = "300"
  statistic           = "Sum"
  threshold           = "1"
  alarm_actions       = [aws_sns_topic.glue_job_failure_notifications.arn]
}