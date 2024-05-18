import os
from logging.config import dictConfig

import structlog
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from dotenv import load_dotenv
from neo4j import GraphDatabase
from shared.models.arxiv_category import ArxivCategory
from shared.models.arxiv_set import ArxivSet
from shared.utils.constants import (
    AIRFLOW_DAGS_ENV_PATH,
    AWS_GLUE_REGISTRY_NAME,
    AWS_REGION,
    AWS_SECRETS_NEO4J_CREDENTIALS,
    AWS_SECRETS_NEO4J_PASSWORD,
    AWS_SECRETS_NEO4J_USERNAME,
    CS_CATEGORIES_INVERTED,
    DEFAULT_LOGGING_ARGS,
    ENVIRONMENT_NAME,
    LOGGING_CONFIG,
    NEO4J_CONNECTION_RETRIES,
    NEO4J_CONNECTION_RETRIES_DEFAULT,
    NEO4J_PASSWORD,
    NEO4J_URI,
    NEO4J_USERNAME,
    ORCHESTRATION_HOST_PRIVATE_IP,
)
from shared.utils.utils import get_aws_secrets

dictConfig(LOGGING_CONFIG)

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()
start_date = days_ago(1)
load_dotenv(dotenv_path=os.getenv(AIRFLOW_DAGS_ENV_PATH))

SERVICE_NAME = "create_arxiv_cs_categories"
TASK_NAME = "create_categories"


def create_categories():
    config = get_config()
    neo4j_driver = GraphDatabase.driver(
        config.get(NEO4J_URI), auth=(config.get(NEO4J_USERNAME), config.get(NEO4J_PASSWORD))
    )
    with neo4j_driver as driver:
        driver.verify_connectivity()
        arxiv_set = ArxivSet(driver, "CS", "Computer Science")
        arxiv_set.create()
        for name, code in CS_CATEGORIES_INVERTED.items():
            arxiv_category = ArxivCategory(driver, code, name)
            arxiv_category.create()
            arxiv_set.relate(
                driver, "CATEGORIZED_BY", ArxivSet.LABEL, arxiv_set.uuid, ArxivCategory.LABEL, arxiv_category.uuid
            )
            arxiv_category.relate(
                driver, "CATEGORIZES", ArxivCategory.LABEL, arxiv_category.uuid, ArxivSet.LABEL, arxiv_set.uuid
            )
    with driver.session() as session:
        driver.verify_connectivity()
        logger.info("Connected to Neo4j")
        session.run("CREATE INDEX arxiv_category_code IF NOT EXISTS FOR (n:ArxivCategory) ON (n.code);")
        session.run("CREATE INDEX arxiv_set_code IF NOT EXISTS FOR (n:ArxivSet) ON (n.code);")
        session.run("CREATE INDEX arxiv_record_uuid IF NOT EXISTS FOR (n:ArxivRecord) ON (n.uuid);")
        session.run("CREATE INDEX arxiv_record_identifier IF NOT EXISTS FOR (n:ArxivRecord) ON (n.identifier);")
        session.run("CREATE INDEX arxiv_record_date IF NOT EXISTS FOR (n:ArxivRecord) ON (n.date);")
        session.run("CREATE INDEX abstract_uuid IF NOT EXISTS FOR (n:Abstract) ON (n.uuid);")
        session.run("CREATE INDEX author_uuid IF NOT EXISTS FOR (n:Author) ON (n.uuid);")
        session.run("CREATE INDEX author_names IF NOT EXISTS FOR (n:Author) ON (n.first_name, n.last_name);")


def get_config() -> dict:
    """
    Gets the config from the environment variables.

    Returns:
        dict: The config.
    """
    try:
        logger.info("Getting config", method=get_config.__name__)
        config = {
            AWS_GLUE_REGISTRY_NAME: os.getenv(AWS_GLUE_REGISTRY_NAME),
            AWS_REGION: os.getenv(AWS_REGION),
            ENVIRONMENT_NAME: os.getenv(ENVIRONMENT_NAME).strip(),
            ORCHESTRATION_HOST_PRIVATE_IP: os.getenv(ORCHESTRATION_HOST_PRIVATE_IP),
        }
        neo4j_retries = (
            int(os.getenv(NEO4J_CONNECTION_RETRIES))
            if os.getenv(NEO4J_CONNECTION_RETRIES)
            else int(os.getenv(NEO4J_CONNECTION_RETRIES_DEFAULT))
        )
        config.update(
            [
                (NEO4J_CONNECTION_RETRIES, neo4j_retries),
            ]
        )
        neo4j_secrets_dict = get_aws_secrets(
            AWS_SECRETS_NEO4J_CREDENTIALS, config.get(AWS_REGION), config.get(ENVIRONMENT_NAME)
        )
        config.update(
            [
                (NEO4J_PASSWORD, neo4j_secrets_dict.get(AWS_SECRETS_NEO4J_PASSWORD, "")),
                (NEO4J_USERNAME, neo4j_secrets_dict.get(AWS_SECRETS_NEO4J_USERNAME, "")),
                (NEO4J_URI, os.getenv(NEO4J_URI).replace("'", "")),
            ]
        )
        if (
            not config.get(AWS_REGION)
            or not config.get(ENVIRONMENT_NAME)
            or not config.get(NEO4J_PASSWORD)
            or not config.get(NEO4J_USERNAME)
            or not config.get(NEO4J_URI)
            or not config.get(ORCHESTRATION_HOST_PRIVATE_IP)
        ):
            logger.error(
                "Config values not found",
                config={k: v for k, v in config.items() if k != NEO4J_PASSWORD},
                method=get_config.__name__,
                task_name=TASK_NAME,
            )
            raise ValueError("Config values not found")
        logger.info(
            "Config values",
            config={k: v for k, v in config.items() if k != NEO4J_PASSWORD},
            method=get_config.__name__,
            neo4j_pass_found=bool(config.get(NEO4J_PASSWORD)),
            task_name=TASK_NAME,
        )
        return config
    except Exception as e:
        logger.error("Failed to get config", error=str(e), method=get_config.__name__, task_name=TASK_NAME)
        raise e


with DAG(
    SERVICE_NAME,
    catchup=False,
    default_args=DEFAULT_LOGGING_ARGS,
    schedule_interval="@hourly",
    start_date=start_date,
    tags=["management", "neo4j", "arxiv"],
) as dag:

    create_arxiv_cs_categories = PythonOperator(
        task_id="create_arxiv_cs_categories",
        python_callable=create_categories,
    )
