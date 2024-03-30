locals {
    app_name            = var.app_name
    aws_region          = var.aws_region
    environment         = var.environment
    runtime             = var.runtime
    service_name        = var.service_name
    service_version     = var.service_version
}

data "archive_file" "services_layer_lambda_function" {
    type        = "zip"
    source_dir  = "../../build/services_layer"
    output_path = "../../build/services_layer/services_layer.zip"
}

resource "aws_lambda_layer_version" "services_layer" {
    layer_name          = "${local.environment}-${local.service_name}"
    filename            = data.archive_file.services_layer_lambda_function.output_path
    source_code_hash    = data.archive_file.services_layer_lambda_function.output_base64sha256
    compatible_runtimes = [local.runtime]
}