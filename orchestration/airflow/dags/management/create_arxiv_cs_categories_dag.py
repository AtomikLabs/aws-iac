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
    CS_CATEGORIES_INVERTED,
    DEFAULT_LOGGING_ARGS,
    ENVIRONMENT_NAME,
    LOGGING_CONFIG,
    NEO4J_PASSWORD,
    NEO4J_URI,
    NEO4J_USERNAME,
    ORCHESTRATION_HOST_PRIVATE_IP,
)
from shared.utils.utils import get_config

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
    env_vars = [
        AWS_GLUE_REGISTRY_NAME,
        AWS_REGION,
        ENVIRONMENT_NAME,
        ORCHESTRATION_HOST_PRIVATE_IP,
    ]
    config = get_config(context=None, env_vars=env_vars, neo4j=True)
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
