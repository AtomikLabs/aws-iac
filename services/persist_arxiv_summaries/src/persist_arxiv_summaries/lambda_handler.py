import json
import logging
import os
import urllib.parse

import structlog
from constants import (
    DATA_BUCKET,
    RECORDS_PREFIX,
    SERVICE_NAME,
    SERVICE_VERSION,
)
from storage_manager import StorageManager

structlog.configure(
    [
        structlog.stdlib.filter_by_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.dict_tracebacks,
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()
logger.setLevel(logging.INFO)

ABSTRACT = "abstract"
ABSTRACT_URL = "abstract_url"
DATE = "date"
IDENTIFIER = "identifier"
PRIMARY_CATEGORY = "primary_category"
TITLE = "title"


def lambda_handler(event, context):
    """
    The main entry point for the Lambda function.

    Args:
        event: The event passed to the Lambda function.
        context: The context passed to the Lambda function.

    Returns:
        The response to be returned to the client.
    """
    try:
        log_initial_info(event)
        bucket_name = event["Records"][0]["s3"]["bucket"]["name"]
        key = urllib.parse.unquote_plus(event["Records"][0]["s3"]["object"]["key"], encoding="utf-8")
        config = get_config()
        storage_manager = StorageManager(bucket_name, logger)
        json_data = json.loads(storage_manager.load(key))
        if not json_data:
            logger.error("No records found", method=lambda_handler.__name__, records_key=key, bucket_name=bucket_name)
            return {"statusCode": 400, "body": "No records found"}
        logger.info(
            "Storing parsed arXiv summary records)} records",
            method=lambda_handler.__name__,
            num_records=len(json_data["records"]),
        )
        for record in json_data["records"]:
            storage_manager.upload_to_s3(f"{config.get(RECORDS_PREFIX)}/{record.get(IDENTIFIER)}/{ABSTRACT}.json", record.get(ABSTRACT))
        return {"statusCode": 200, "body": "Success"}
    except Exception as e:
        logger.error("An error occurred", method=lambda_handler.__name__, error=str(e))
        return {"statusCode": 500, "body": "Internal server error", "error": str(e), "event": event}


def log_initial_info(event: dict) -> None:
    """
    Logs initial info.

    Args:
        event (dict): Event.
    """
    try:
        logger.debug(
            "Log variables",
            method=log_initial_info.__name__,
            log_group=os.environ["AWS_LAMBDA_LOG_GROUP_NAME"],
            log_stream=os.environ["AWS_LAMBDA_LOG_STREAM_NAME"],
        )
        logger.debug("Running on", method=log_initial_info.__name__, platform="AWS")
    except KeyError:
        logger.debug("Running on", method=log_initial_info.__name__, platform="CI/CD or local")
    logger.debug("Event received", method=log_initial_info.__name__, trigger_event=event)


def get_config() -> dict:
    """
    Gets the config from the environment variables.

    Returns:
        dict: The config.
    """
    try:
        config = {
            DATA_BUCKET: os.environ[DATA_BUCKET],
            RECORDS_PREFIX: os.environ[RECORDS_PREFIX],
            SERVICE_NAME: os.environ[SERVICE_NAME],
            SERVICE_VERSION: os.environ[SERVICE_VERSION],
        }
        logger.debug("Config", method=get_config.__name__, config=config)
    except KeyError as e:
        logger.error("Missing environment variable", method=get_config.__name__, error=str(e))
        raise e
    logger.debug("Config", method=get_config.__name__, config=config)
    return config
