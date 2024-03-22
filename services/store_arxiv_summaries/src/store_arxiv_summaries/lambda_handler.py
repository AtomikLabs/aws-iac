import json
import os
from typing import Dict, List

import structlog
import urllib.parse
from constants import APP_NAME, DATA_BUCKET, ENVIRONMENT_NAME, ETL_KEY_PREFIX, S3_KEY_DATE_FORMAT, SERVICE_NAME, SERVICE_VERSION
from neo4j_manager import Neo4jDatabase
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
)

logger = structlog.get_logger()

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
        config = get_config()
        bucket_name = event["Records"][0]["s3"]["bucket"]["name"]
        key = urllib.parse.unquote_plus(event["Records"][0]["s3"]["object"]["key"], encoding="utf-8")
        storage_manager = StorageManager(bucket_name, logger)
        json_data = json.loads(storage_manager.load(key))
        if not json_data or not json_data.get("records"):
            logger.error("No records found", method=lambda_handler.__name__, records_key=key, bucket_name=bucket_name)
            return {"statusCode": 400, "body": "No records found"}
        logger.info(
            "Storing parsed arXiv summary records)} records",
            method=lambda_handler.__name__,
            num_records=len(json_data["records"]),
        )
        store_records(json_data.get("records"), bucket_name, key)
        return {"statusCode": 200, "body": "Success"}
    except Exception as e:
        logger.error(
            "An error occurred",
            method=lambda_handler.__name__,
            error=str(e),
        )
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
            APP_NAME: os.environ[APP_NAME],
            DATA_BUCKET: os.environ[DATA_BUCKET],
            ENVIRONMENT_NAME: os.environ[ENVIRONMENT_NAME],
            ETL_KEY_PREFIX: os.environ[ETL_KEY_PREFIX],
            SERVICE_NAME: os.environ[SERVICE_NAME],
            SERVICE_VERSION: os.environ[SERVICE_VERSION],
        }
        logger.debug("Config", method=get_config.__name__, config=config)
    except KeyError as e:
        logger.error("Missing environment variable", method=get_config.__name__, error=str(e))
        raise e
    logger.debug("Config", method=get_config.__name__, config=config)
    return config


def store_records(records: List[Dict], bucket_name:str, key: str) -> int:
    """
    Stores arxiv research summary records in the neo4j database.

    Args:
        records (List[Dict]): The arXiv records to store.
        bucket_name (str): The S3 bucket name for the parsed arXiv records.
        key (str): The S3 key for the parsed arXiv records.

    Returns:
        int: The number of records stored.
    """
    if not records or not isinstance(records, list):
        logger.error(
            "Records must be present and be a list of dict.",
            method=store_records.__name__,
            records_type=type(records),
            records=records,
        )
        raise ValueError("Records must be present and be a list of dict.")
    if not key or not isinstance(key, str):
        logger.error(
            "Key for parsed records must be present and be a string.",
            method=store_records.__name__,
            key_type=type(key),
            key=key,
        )
        raise ValueError("Key must be present and be a string.")
    total = len(records)
    malformed_records = []
    well_formed_records = []
    required_fields = ["identifier", "title", "authors", "group", "abstract", "date", "abstract_url"]
    try:
        for record in records:
            if not all(record.get(field) for field in required_fields) or len(record.get("authors", [])) < 1:
                malformed_records.append(record)
                logger.error("Malformed record", method=store_records.__name__, record=record)
            else:
                well_formed_records.append(record)

        if malformed_records:
            logger.warning(
                "Malformed records",
                method=store_records.__name__,
                num_malformed_records=len(malformed_records),
                malformed_records=malformed_records,
            )
        if well_formed_records:
            logger.info(
                "Storing well formed records",
                method=store_records.__name__,
                num_well_formed_records=len(well_formed_records),
            )
            db = Neo4jDatabase(logger)
            db.store_arxiv_records(well_formed_records)
            logger.info("Stored records", method=store_records.__name__, num_records=len(well_formed_records))

    except Exception as e:
        logger.error("An error occurred", method=store_records.__name__, error=str(e))
        raise e
    finally:
        logger.info(
            "Finished storing records",
            method=store_records.__name__,
            num_records=total,
            num_malformed_records=len(malformed_records),
            num_well_formed_records=len(well_formed_records),
        )
