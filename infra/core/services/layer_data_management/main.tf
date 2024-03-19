locals {
    app_name            = var.app_name
    aws_region          = var.aws_region
    environment         = var.environment
    runtime             = var.runtime
    service_name        = var.service_name
    service_version     = var.service_version
}

data "archive_file" "layer_data_management_lambda_function" {
    type        = "zip"
    source_dir  = "../../build/layer_data_management"
    output_path = "../../build/layer_data_management/layer_data_management.zip"
}

resource "aws_lambda_layer_version" "layer_data_management" {
    layer_name          = "${local.environment}-${local.service_name}"
    filename            = data.archive_file.layer_data_management_lambda_function.output_path
    source_code_hash    = data.archive_file.layer_data_management_lambda_function.output_base64sha256
    compatible_runtimes = [local.runtime]
}