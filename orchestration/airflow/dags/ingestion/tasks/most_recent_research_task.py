import os
from datetime import timedelta
from logging.config import dictConfig

import structlog
from dotenv import load_dotenv
from neo4j import GraphDatabase
from shared.utils.constants import (
    AIRFLOW_DAGS_ENV_PATH,
    AIRFLOW_DATA_INTERVAL_START,
    AIRFLOW_RUN_ID,
    ARXIV_INGESTION_DAY_SPAN,
    AWS_REGION,
    AWS_SECRETS_NEO4J_CREDENTIALS,
    ENVIRONMENT_NAME,
    INGESTION_EARLIEST_DATE,
    LOGGING_CONFIG,
    NEO4J_CONNECTION_RETRIES,
    NEO4J_CONNECTION_RETRIES_DEFAULT,
    NEO4J_PASSWORD,
    NEO4J_URI,
    NEO4J_USERNAME,
    PASSWORD,
    RESEARCH_RECORD_DATE,
    USERNAME,
)
from shared.utils.utils import get_aws_secrets, get_storage_key_datetime

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
load_dotenv(dotenv_path=AIRFLOW_DAGS_ENV_PATH)

TASK_NAME = "most_recent_research"


def run(**context: dict):
    try:
        logger.info(
            f"Running {TASK_NAME} task",
            task_name=TASK_NAME,
            date=context.get(AIRFLOW_DATA_INTERVAL_START),
            run_id=context.get(AIRFLOW_RUN_ID),
        )
        config = get_config()
        earliest_date = get_earliest_date(config)
        logger.info(f"Earliest date: {earliest_date}", method=run.__name__, task_name=TASK_NAME)
        context.get("ti").xcom_push(key=INGESTION_EARLIEST_DATE, value=earliest_date)
        logger.info("context", context=context, method=run.__name__, task_name=TASK_NAME)
    except Exception as e:
        logger.error(f"Failed to run {TASK_NAME} task", error=str(e), method=run.__name__, task_name=TASK_NAME)
        raise e


def get_config() -> dict:
    """
    Gets the config from the environment variables.

    Returns:
        dict: The config.
    """
    try:
        config = {
            ARXIV_INGESTION_DAY_SPAN: os.getenv(ARXIV_INGESTION_DAY_SPAN),
            AWS_REGION: os.getenv(AWS_REGION),
            ENVIRONMENT_NAME: os.getenv(ENVIRONMENT_NAME),
            NEO4J_CONNECTION_RETRIES: os.getenv(NEO4J_CONNECTION_RETRIES,
                                                NEO4J_CONNECTION_RETRIES_DEFAULT),
        }
        neo4j_secrets_dict = get_aws_secrets(AWS_SECRETS_NEO4J_CREDENTIALS,
                                             config.get(AWS_REGION),
                                             config.get(ENVIRONMENT_NAME))
        config = {
            NEO4J_PASSWORD: neo4j_secrets_dict.get(PASSWORD, ""),
            NEO4J_USERNAME: neo4j_secrets_dict.get(USERNAME, ""),
            NEO4J_URI: os.getenv(NEO4J_URI),
        }
        if (
            not config.get(ARXIV_INGESTION_DAY_SPAN)
            or not config.get(ENVIRONMENT_NAME)
            or not config.get(NEO4J_PASSWORD)
            or not config.get(NEO4J_USERNAME)
            or not config.get(NEO4J_URI)
        ):
            logger.error(
                "Config values not found",
                config={k: v for k, v in config.items() if k != NEO4J_PASSWORD},
                method=get_config.__name__,
                task_name=TASK_NAME,
            )
            raise ValueError("Config values not found")
        return config
    except Exception as e:
        logger.error("Failed to get config", error=str(e), method=get_config.__name__, task_name=TASK_NAME)
        raise e


def get_earliest_date(config: dict) -> str:
    """
    Gets the earliest date to fetch data from.

    Args:
        config (dict): The config.

    Returns:
        str: The earliest date.
    """
    earliest = get_storage_key_datetime().date() - timedelta(days=config.get(ARXIV_INGESTION_DAY_SPAN))
    retries = 0
    while retries < int(config.get(NEO4J_CONNECTION_RETRIES)):
        try:
            with GraphDatabase.driver(
                config.get(NEO4J_URI), auth=(config.get(NEO4J_USERNAME), config.get(NEO4J_PASSWORD))
            ) as driver:
                records, _, _ = driver.execute_query(
                    """
                    MATCH (r:ArxivRecord)
                    RETURN r
                    ORDER BY r.date DESC
                    LIMIT 1
                    """
                )
                if records:
                    try:
                        record = records[0]
                        next_date = record.data().get("r", {}).get(RESEARCH_RECORD_DATE, None).to_native()
                        next_date = next_date + timedelta(days=1)
                        if next_date:
                            earliest = max(earliest, next_date)
                    except Exception as e:
                        logger.error(
                            "Failed to get research date from record",
                            error=str(e),
                            method=get_earliest_date.__name__,
                            task_name=TASK_NAME,
                        )
            logger.info(
                "Earliest date",
                earliest=earliest.strftime("%Y-%m-%d"),
                method=get_earliest_date.__name__,
                task_name=TASK_NAME,
            )
            return earliest.strftime("%Y-%m-%d")
        except Exception as e:
            if "Neo.ClientError.Security.AuthenticationRateLimit" in str(e):
                logger.warning(
                    "Rate limited by Neo4j", method=get_earliest_date.__name__, retries=retries, task_name=TASK_NAME
                )
                retries += 1
                continue
            logger.error(
                "Failed to get earliest date", error=str(e), method=get_earliest_date.__name__, task_name=TASK_NAME
            )
            raise e
