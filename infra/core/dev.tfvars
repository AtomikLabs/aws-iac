# **********************************************************
# * Core Config                                            *
# **********************************************************

app_name = "atomiklabs"
app_version = "0.3.3-alpha"
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
neo4j_connection_retries = 4
neo4j_instance_type = "t3a.medium"
neo4j_key_pair_name = "atomiklabs-neo4j-keypair"
neo4j_resource_prefix = "data-management-neo4j"
neo4j_host_username = "ec2-user"
records_prefix = "processed_data/research_records"

# **********************************************************
# * Orchestration                                          *
# **********************************************************

airflow_dags_env_path = "/opt/airflow/dags/.env"
orchestration_ami_id = "ami-0f403e3180720dd7e"
orchestration_instance_type = "t3a.large"
orchestration_key_pair_name = "atomiklabs-orchestration-keypair"
orchestration_resource_prefix = "orchestration"
orchestration_username = "ec2-user"

# **********************************************************
# * Security                                               *
# **********************************************************

bastion_ami_id = "ami-0f403e3180720dd7e"
bastion_host_key_pair_name = "atomiklabs-bastion-keypair"
bastion_instance_type = "t2.micro"
bastion_host_username = "ec2-user"

# **********************************************************
# * Services                                               *
# **********************************************************

arxiv_api_max_retries = 5
arxiv_base_url = "http://export.arxiv.org/oai2"
arxiv_ingestion_day_span = 5
arxiv_sets = ["cs"]
default_lambda_runtime = "python3.10"

fetch_from_arxiv_task_version = "0.1.0"
most_recent_research_records_version = "0.0.2"
parse_summaries_task_version = "0.1.0"
persist_summaries_task_version = "0.0.1"
save_summaries_to_datalake_task_version = "0.0.1"
