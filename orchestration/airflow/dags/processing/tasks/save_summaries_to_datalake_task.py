import json
import os
from logging.config import dictConfig

import structlog
from dotenv import load_dotenv
from shared.database.s3_manager import S3Manager
from shared.utils.constants import (
    AIRFLOW_DAGS_ENV_PATH,
    AWS_REGION,
    DATA_BUCKET,
    ENVIRONMENT_NAME,
    KAFKA_LISTENER,
    LOGGING_CONFIG,
    RECORDS_PREFIX,
    SAVE_SUMMARIES_TO_DATALAKE_TASK_VERSION,
    SCHEMA,
    SERVICE_NAME,
    SERVICE_VERSION,
)

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

ABSTRACT = "abstract"
ABSTRACT_URL = "abstract_url"
DATE = "date"
IDENTIFIER = "identifier"
PRIMARY_CATEGORY = "primary_category"
TITLE = "title"

TASK_NAME = "save_summaries_to_datalake"


def run(**context: dict):
    try:
        logger.info("Running save_summaries_to_datalake_task")
        config = get_config(context)
        schema = context["ti"].xcom_pull(task_ids=KAFKA_LISTENER, key=SCHEMA)
        logger.info("Schema", method=run.__name__, schema=schema)
        s3_manager = S3Manager(os.getenv(DATA_BUCKET), logger)
        json_data = json.loads(s3_manager.load(schema.get("s3_key")))
        if not json_data:
            logger.error("No records found", method=run.__name__, records_key=schema.get("s3_key"))
            return {"statusCode": 400, "body": "No records found"}
        logger.info(
            "Storing parsed arXiv summary records)} records",
            method=run.__name__,
            num_records=len(json_data["records"]),
        )
        for record in json_data["records"]:
            s3_manager.upload_to_s3(
                f"{config.get(RECORDS_PREFIX)}/{record.get(IDENTIFIER)}/{ABSTRACT}.json", record.get(ABSTRACT)
            )
        return {"statusCode": 200, "body": "Success"}
    except Exception as e:
        logger.error("Error running save_summaries_to_datalake_task", method=run.__name__, error=e)
        raise e


def get_config(context: dict) -> dict:
    """
    Gets the config from the environment variables.

    Returns:
        dict: The config.
    """
    try:
        logger.info("Getting config", method=get_config.__name__, task_name=TASK_NAME)
        config = {
            AWS_REGION: os.getenv(AWS_REGION),
            ENVIRONMENT_NAME: os.getenv(ENVIRONMENT_NAME),
            DATA_BUCKET: os.getenv(DATA_BUCKET),
            RECORDS_PREFIX: os.getenv(RECORDS_PREFIX),
            SERVICE_NAME: TASK_NAME,
            SERVICE_VERSION: os.getenv(SAVE_SUMMARIES_TO_DATALAKE_TASK_VERSION),
        }

        if (
            not config.get(AWS_REGION)
            or not config.get(ENVIRONMENT_NAME)
            or not config.get(DATA_BUCKET)
            or not config.get(RECORDS_PREFIX)
            or not config.get(SERVICE_NAME)
            or not config.get(SERVICE_VERSION)
        ):
            raise ValueError("Missing config values")
    except Exception as e:
        logger.error("Error getting config", method=get_config.__name__, task_name=TASK_NAME, error=e)
        raise e
