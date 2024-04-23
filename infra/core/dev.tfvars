# **********************************************************
# * Core Config                                            *
# **********************************************************

app_name = "atomiklabs"
app_version = "0.0.4"
availability_zones = ["us-east-1a", "us-east-1b", "us-east-1c"]
aws_region = "us-east-1"
backend_dynamodb_table = "terraform-state-locks"
default_ami_id = "ami-0f403e3180720dd7e"
environment = "dev"
iam_user_name = "atomiklabs-dev-ci-cd"
infra_config_bucket = "atomiklabs-infra-config-bucket"
infra_config_bucket_arn = "arn:aws:s3:::atomiklabs-infra-config-bucket"
infra_config_prefix = "terraform/terraform.state"
repo = "github.com/AtomikLabs/atomiklabs"
terraform_aws_region = "us-east-1"
terraform_outputs_prefix = "terraform-outputs"

# **********************************************************
# * Data Management                                        *
# **********************************************************

data_ingestion_key_prefix = "raw_data/data_ingestion"
data_ingestion_metadata_key_prefix = "raw_data/data_ingestion/metadata"
etl_key_prefix = "processed_data/etl"
neo4j_ami_id = "ami-0f403e3180720dd7e"
neo4j_instance_type = "t3a.large"
neo4j_key_pair_name = "atomiklabs-neo4j-keypair"
neo4j_resource_prefix = "data-management-neo4j"
records_prefix = "processed_data/research_records"

# **********************************************************
# * Security                                               *
# **********************************************************

bastion_host_key_pair_name = "atomiklabs-bastion-keypair"

# **********************************************************
# * Services                                               *
# **********************************************************

arxiv_base_url = "http://export.arxiv.org/oai2"
arxiv_summary_set = "cs"
default_lambda_runtime = "python3.10"

# services_layer
services_layer_service_name = "services_layer"
services_layer_service_version = "0.1.0"

# fetch_daily_summaries
fetch_daily_summaries_max_retries = 10
fetch_daily_summaries_service_name = "fetch_daily_summaries"
fetch_daily_summaries_service_version = "0.1.0"

# parse_arxiv_summaries
parse_arxiv_summaries_service_name = "parse_arxiv_summaries"
parse_arxiv_summaries_service_version = "0.1.0"

# post_arxiv_parse_dispatcher
post_arxiv_parse_dispatcher_service_name = "post_arxiv_parse_dispatcher"
post_arxiv_parse_dispatcher_service_version = "0.0.1"

# store_arxiv_summaries
store_arxiv_summaries_service_name = "store_arxiv_summaries"
store_arxiv_summaries_service_version = "0.1.0"

# persist_arxiv_summaries
persist_arxiv_summaries_service_name = "persist_arxiv_summaries"
persist_arxiv_summaries_service_version = "0.0.1"