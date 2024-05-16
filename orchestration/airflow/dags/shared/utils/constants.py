from datetime import datetime

# Airflow
AIRFLOW_DATA_INTERVAL_START = "data_interval_start"
AIRFLOW_RUN_ID = "run_id"
AIRFLOW_DAGS_ENV_PATH = "AIRFLOW_DAGS_ENV_PATH"

# Arxiv
CS_CATEGORIES_INVERTED = {
    "Computer Science - Artificial Intelligence": "AI",
    "Computer Science - Hardware Architecture": "AR",
    "Computer Science - Computational Complexity": "CC",
    "Computer Science - Computational Engineering, Finance, and Science": "CE",
    "Computer Science - Computational Geometry": "CG",
    "Computer Science - Computation and Language": "CL",
    "Computer Science - Cryptography and Security": "CR",
    "Computer Science - Computer Vision and Pattern Recognition": "CV",
    "Computer Science - Computers and Society": "CY",
    "Computer Science - Databases": "DB",
    "Computer Science - Distributed, Parallel, and Cluster Computing": "DC",
    "Computer Science - Digital Libraries": "DL",
    "Computer Science - Discrete Mathematics": "DM",
    "Computer Science - Data Structures and Algorithms": "DS",
    "Computer Science - Emerging Technologies": "ET",
    "Computer Science - Formal Languages and Automata Theory": "FL",
    "Computer Science - General Literature": "GL",
    "Computer Science - Graphics": "GR",
    "Computer Science - Computer Science and Game Theory": "GT",
    "Computer Science - Human-Computer Interaction": "HC",
    "Computer Science - Information Retrieval": "IR",
    "Computer Science - Information Theory": "IT",
    "Computer Science - Machine Learning": "LG",
    "Computer Science - Logic in Computer Science": "LO",
    "Computer Science - Multiagent Systems": "MA",
    "Computer Science - Multimedia": "MM",
    "Computer Science - Mathematical Software": "MS",
    "Computer Science - Numerical Analysis": "NA",
    "Computer Science - Neural and Evolutionary Computing": "NE",
    "Computer Science - Networking and Internet Architecture": "NI",
    "Computer Science - Other Computer Science": "OH",
    "Computer Science - Operating Systems": "OS",
    "Computer Science - Performance": "PF",
    "Computer Science - Programming Languages": "PL",
    "Computer Science - Robotics": "RO",
    "Computer Science - Symbolic Computation": "SC",
    "Computer Science - Sound": "SD",
    "Computer Science - Software Engineering": "SE",
    "Computer Science - Social and Information Networks": "SI",
    "Computer Science - Systems and Control": "SY",
}

# AWS
AWS_REGION = "AWS_REGION"
AWS_SECRETS_MANAGER = "secretsmanager"
AWS_SECRETS_NEO4J_CREDENTIALS = "neo4j-credentials"
AWS_SECRETS_NEO4J_PASSWORD = "neo4j_password"
AWS_SECRETS_NEO4J_USERNAME = "neo4j_username"
AWS_SECRETS_STRING = "SecretString"

# Databases
DATA_BUCKET = "DATA_BUCKET"
DEFAULT_NEO4J_DB = "neo4j"  # supposed to be lower case
NEO4J_CONNECTION_RETRIES = "NEO4J_CONNECTION_RETRIES"
NEO4J_CONNECTION_RETRIES_DEFAULT = 4

# Dates
ARXIV_RESEARCH_DATE_FORMAT = "%Y-%m-%d"
DEFAULT_TIMEZONE = "US/Pacific"
S3_KEY_DATE_FORMAT = "%Y-%m-%dT%H-%M-%S"

# Error Messages
FAILED_TO_CREATE_ABSTRACT = "Failed to create Abstract"
FAILED_TO_CREATE_ARXIV_CATEGORY = "Failed to create ArxivCategory"
FAILED_TO_CREATE_ARXIV_RECORD = "Failed to create ArxivRecord"
FAILED_TO_CREATE_ARXIV_SET = "Failed to create ArxivSet"
FAILED_TO_CREATE_AUTHOR = "Failed to create Author"
FAILED_TO_CREATE_DATA = "Failed to create Data"
FAILED_TO_CREATE_DATA_OPERATION = "Failed to create DataOperation"
FAILED_TO_CREATE_DATA_SOURCE = "Failed to create DataSource"
FAILED_TO_CREATE_FULL_TEXT = "Failed to create FullText"
INTERNAL_SERVER_ERROR = "Internal server error"

# General
PASSWORD = "password"
USERNAME = "username"

# Logging
DEFAULT_LOGGING_ARGS = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2024, 4, 26),
    "retries": 1,
}

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "plain": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "plain",
        },
    },
    "loggers": {
        "": {
            "handlers": ["console"],
            "level": "INFO",
        },
    },
}

# Neo4j
AUTHORS = "AUTHORS"
AUTHORED_BY = "AUTHORED_BY"
CATEGORIZES = "CATEGORIZES"
CATEGORIZED_BY = "CATEGORIZED_BY"
CREATES = "CREATES"
CREATED_BY = "CREATED_BY"
DOCUMENTED_BY = "DOCUMENTED_BY"
DOCUMENTS = "DOCUMENTS"
INGESTS = "INGESTS"
INGESTED_BY = "INGESTED_BY"
LOADS = "LOADS"
LOADED_BY = "LOADED_BY"
OBTAINS_FROM = "OBTAINS_FROM"
PARSED_BY = "PARSED_BY"
PARSES = "PARSES"
PRIMARILY_CATEGORIZED_BY = "PRIMARILY_CATEGORIZED_BY"
PROVIDES = "PROVIDES"
RESEARCH_RECORD_DATE = "date"
SUMMARIZED_BY = "SUMMARIZED_BY"
SUMMARIZES = "SUMMARIZES"

# Schema Registry
AWS_GLUE_REGISTRY_NAME = "AWS_GLUE_REGISTRY_NAME"

# Schemas
ARXIV_RESEARCH_INGESTION_EVENT_SCHEMA = "arxiv_research_ingestion_event_schema"
ARXIV_RESEARCH_INGESTION_EVENT_SCHEMA_ENV = "ARXIV_RESEARCH_INGESTION_EVENT_SCHEMA"
COMPLETED = "COMPLETED"
FAILED = "FAILED"
IN_PROGRESS = "IN_PROGRESS"
SCHEMA_DEFINITION = "SchemaDefinition"

# Services
APP_NAME = "APP_NAME"
ARXIV_API_MAX_RETRIES = "ARXIV_API_MAX_RETRIES"
ARXIV_BASE_URL = "ARXIV_BASE_URL"
ARXIV_INGESTION_DAY_SPAN = "ARXIV_INGESTION_DAY_SPAN"
ARXIV_SETS = "ARXIV_SETS"
DATA_INGESTION_KEY_PREFIX = "DATA_INGESTION_KEY_PREFIX"
DATA_ARXIV_SUMMARIES_INGESTION_COMPLETE_TOPIC = "data_arxiv_summaries_ingestion_complete"
DISPATCH_LAMBDA_NAMES = "DISPATCH_LAMBDA_NAMES"
ENVIRONMENT_NAME = "ENVIRONMENT_NAME"
ETL_KEY_PREFIX = "ETL_KEY_PREFIX"
FETCH_FROM_ARXIV_TASK_VERSION = "FETCH_FROM_ARXIV_TASK_VERSION"
KAFKA_LISTENER = "kafka_listener"
INGESTION_EARLIEST_DATE = "EARLIEST_DATE"
MOST_RECENT_RESEARCH_TASK_VERSION = "MOST_RECENT_RESEARCH_TASK_VERSION"
NEO4J_PASSWORD = "NEO4J_PASSWORD"
NEO4J_URI = "NEO4J_URI"
NEO4J_USERNAME = "NEO4J_USERNAME"
ORCHESTRATION_HOST_PRIVATE_IP = "ORCHESTRATION_HOST_PRIVATE_IP"
RAW_DATA_KEYS = "RAW_DATA_KEYS"
RECORDS_PREFIX = "RECORDS_PREFIX"
SCHEMA = "SCHEMA"
SERVICE_NAME = "SERVICE_NAME"
SERVICE_VERSION = "SERVICE_VERSION"

# Storage
ETL = "etl"
JSON = "json"
PROCESSED_DATA = "processed_data"
RESEARCH_RECORDS = "research_records"
XML = "xml"
