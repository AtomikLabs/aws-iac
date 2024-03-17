# **********************************************************
# * Core Config                                            *
# **********************************************************

app_name = "atomiklabs"
app_version = "0.0.4"
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
neo4j_ami_id = "ami-0f403e3180720dd7e"
neo4j_instance_type = "t3a.small"
neo4j_key_pair_name = "atomiklabs-neo4j-keypair"
neo4j_resource_prefix = "data-management-neo4j"

# **********************************************************
# * Security                                               *
# **********************************************************

bastion_host_key_pair_name = "atomiklabs-bastion-keypair"

# **********************************************************
# * Services                                               *
# **********************************************************

arxiv_base_url = "http://export.arxiv.org/oai2"
arxiv_summary_sets = ["cs"]
default_lambda_runtime = "python3.10"
zip_key_prefix = "services/code"


# fetch_daily_summaries

fetch_daily_summaries_max_retries = 10
fetch_daily_summaries_service_name = "fetch_daily_Summaries"
fetch_daily_summaries_service_version = "0.0.1"

# parase_arxiv_summaries

parse_arxiv_summaries_name = "parse_arxiv_summaries"
parse_arxiv_summaries_version = "0.0.1"
