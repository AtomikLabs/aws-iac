terraform {
    backend "s3" {
        bucket          = "atomiklabs-infra-config-bucket"
        key             = "terraform/terraform.state"
        region          = "us-east-1"
        dynamodb_table = "atomiklabs-terraform-lock-table"
        encrypt         = true
    }
}