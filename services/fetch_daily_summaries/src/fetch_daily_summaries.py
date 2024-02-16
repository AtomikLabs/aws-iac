# Description: Lambda function to fetch daily summaries from arXiv.

import json
import logging
import os
import time
from datetime import datetime, timedelta

import boto3
import defusedxml.ElementTree as ET
import requests
import structlog
from src.data_ingestion_metadata import DataIngestionMetadata

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
BACKOFF_TIMES = [30, 120]
DAY_SPAN = 5
S3_STORAGE_PREFIX = "data-ingestion/raw/fetch-daily-summaries/"

# Environment variables
APP_NAME = "app_name"
BASE_URL_STR = "base_url"
ENVIRONMENT_NAME = "environment"
GLUE_DATABASE_NAME = "glue_database_name"
GLUE_TABLE_NAME = "glue_table_name"
S3_BUCKET_NAME = "s3_bucket_name"
S3_STORAGE_KEY_PREFIX_NAME = "s3_storage_prefix"
SUMMARY_SET_STR = "summary_set"

# Logging constants
FETCH_DATA = "fetch_daily_summaries.fetch_data"
GET_CONFIG = "fetch_daily_summaries.get_config"
GET_EARLIEST_DATE = "fetch_daily_summaries.get_earliest_date"
GET_STORAGE_KEY = "fetch_daily_summaries.get_storage_key"
LAMBDA_HANDLER = "fetch_daily_summaries.lambda_handler"
LAMBDA_NAME = "fetch_daily_summaries"
LOG_INITIAL_INFO = "fetch_daily_summaries.log_initial_info"
PERSIST_TO_S3 = "fetch_daily_summaries.persist_to_s3"


def lambda_handler(event: dict, context) -> dict:
    """
    The main entry point for the Lambda function.

    Args:
        event (dict): The event data.
        context: The context data.

    Returns:
        dict: A dict with the status code and body.
    """
    try:
        log_initial_info(event)

        config = get_config()

        metadata = DataIngestionMetadata(
            app_name=config[APP_NAME],
            date_time=datetime.now(),
            database_name=config[GLUE_DATABASE_NAME],
            environment=config[ENVIRONMENT_NAME],
            function_name=context.function_name,
            raw_data_bucket=config[S3_BUCKET_NAME],
            table_name=config[GLUE_TABLE_NAME],
        )

        today = datetime.today().date()
        earliest = today - timedelta(days=DAY_SPAN)
        metadata.today = today.strftime(DataIngestionMetadata.DATETIME_FORMAT)
        metadata.earliest = earliest.strftime(DataIngestionMetadata.DATETIME_FORMAT)

        xml_data_list = fetch_data(config.get(BASE_URL_STR), earliest, config.get(SUMMARY_SET_STR), metadata)

        metadata.raw_data_key = get_storage_key(config)
        content_str = json.dumps(xml_data_list)
        persist_to_s3(content_str, metadata)

        logger.info("Fetching arXiv summaries succeeded", method=LAMBDA_HANDLER, status=200, body="Success")
        return {"statusCode": 200, "body": json.dumps({"message": "Success"})}

    except Exception as e:
        logger.exception(
            "Fetching arXiv daily summaries failed",
            method=LAMBDA_HANDLER,
            status=500,
            body="Internal Server Error",
            error=str(e),
        )
        metadata.error_message = str(e)
        metadata.status = "failure"
        return {"statusCode": 500, "body": json.dumps({"message": "Internal Server Error"})}


def get_config() -> dict:
    """
    Gets the config from the environment variables.

    Returns:
        dict: The config.
    """
    try:
        config = {
            APP_NAME: os.environ["APP_NAME"],
            BASE_URL_STR: "http://export.arxiv.org/oai2",
            ENVIRONMENT_NAME: os.environ["ENVIRONMENT"],
            GLUE_DATABASE_NAME: os.environ["GLUE_DATABASE_NAME"],
            GLUE_TABLE_NAME: os.environ["GLUE_TABLE_NAME"],
            S3_BUCKET_NAME: os.environ["S3_BUCKET_NAME"],
            S3_STORAGE_KEY_PREFIX_NAME: os.environ.get("S3_STORAGE_KEY_PREFIX", S3_STORAGE_PREFIX),
            SUMMARY_SET_STR: "cs",
        }
        logger.debug("Config", method=GET_CONFIG, config=config)
    except KeyError as e:
        logger.error("Missing environment variable", method=GET_CONFIG, error=str(e))
        raise e

    return config


def log_initial_info(event: dict) -> None:
    """
    Logs initial info.

    Args:
        event (dict): Event.
    """
    try:
        logger.debug(
            "Log variables",
            method=LOG_INITIAL_INFO,
            log_group=os.environ["AWS_LAMBDA_LOG_GROUP_NAME"],
            log_stream=os.environ["AWS_LAMBDA_LOG_STREAM_NAME"],
        )
        logger.debug("Running on", method=LOG_INITIAL_INFO, platform="AWS")
    except KeyError:
        logger.debug("Running on", method=LOG_INITIAL_INFO, platform="CI/CD or local")
    logger.debug("Event received", method=LOG_INITIAL_INFO, trigger_event=event)


def fetch_data(base_url: str, from_date: str, set: str, metadata: DataIngestionMetadata) -> list:
    """
    Fetches data from arXiv.

    Args:
        base_url (str): Base URL.
        from_date (str): From date.
        set (str): Set.
        metadata (DataIngestionMetadata): Metadata.

    Returns:
        list: List of XML responses.

    Raises:
        ValueError: If base URL is not provided.
        ValueError: If from date is not provided.
        ValueError: If set is not provided.
        ValueError: If metadata is not provided.
    """
    if not base_url:
        logger.error("Base URL is required", method=FETCH_DATA)
        raise ValueError("Base URL is required")

    if not from_date:
        logger.error("From date is required", method=FETCH_DATA)
        raise ValueError("From date is required")

    if not set:
        logger.error("Set is required", method=FETCH_DATA)
        raise ValueError("Set is required")

    if not metadata:
        logger.error("Metadata is required", method=FETCH_DATA)
        raise ValueError("Metadata is required")

    backoff_times = BACKOFF_TIMES.copy()
    full_xml_responses = []
    params = {"verb": "ListRecords", "set": set, "metadataPrefix": "oai_dc", "from": from_date}
    retries = 0
    while retries < len(BACKOFF_TIMES):
        try:
            logger.info(
                "Fetching data from arXiv",
                method=FETCH_DATA,
                base_url=base_url,
                params=params,
                retries=retries,
                backoff_times=backoff_times,
            )
            response = requests.get(base_url, params=params, timeout=60)
            metadata.uri = response.request.url
            metadata.size_of_data_downloaded = str(calculate_mb(len(response.content))) + " MB"
            response.raise_for_status()
            full_xml_responses.append(response.text)
            root = ET.fromstring(response.content)
            resumption_token_element = root.find(".//{http://www.openarchives.org/OAI/2.0/}resumptionToken")

            if resumption_token_element is not None and resumption_token_element.text:
                logger.debug(
                    "Resumption token found", method=FETCH_DATA, resumption_token=resumption_token_element.text
                )
                time.sleep(5)
                params = {"verb": "ListRecords", "resumptionToken": resumption_token_element.text}
                retries += 1
            else:
                break

        except requests.exceptions.HTTPError as e:
            logger.exception("Error occurred while fetching data from arXiv", method=FETCH_DATA, error=str(e))

            if response.status_code == 503:
                backoff_time = response.headers.get("Retry-After", backoff_times.pop(0) if backoff_times else None)
                if backoff_time is None:
                    logger.exception("Exhausted all backoff times", method=FETCH_DATA)
                    break
                logger.warning("Retrying after backoff time", method=FETCH_DATA, backoff_time=backoff_time)
                time.sleep(int(backoff_time))
            else:
                break

        except Exception as e:
            logging.exception("Error occurred while fetching data from arXiv", method=FETCH_DATA, error=str(e))
            break
    logger.info("Fetched data from arXiv", method=FETCH_DATA, full_xml_responses=full_xml_responses)
    return full_xml_responses


def calculate_mb(size: int) -> float:
    """
    Converts bytes to MB.

    Args:
        size (int): Size in bytes.

    Returns:
        float: Size in MB to two decimal places.
    """
    return round(size / (1024 * 1024), 2)


def get_storage_key(config: dict) -> str:
    """
    Gets the storage key for the S3 bucket.

    Args:
        config (dict): The config.

    Returns:
        str: The storage key.

    Raises:
        ValueError: If config is not provided.
    """
    if not config:
        logger.error("Config is required", method=GET_STORAGE_KEY)
        raise ValueError("Config is required")

    key_date = time.strftime(DataIngestionMetadata.S3_KEY_DATE_FORMAT)
    key = f"{config.get(S3_STORAGE_KEY_PREFIX_NAME)}/{key_date}.json"
    logger.info("Storage key", method=GET_STORAGE_KEY, key=key)
    return key


def persist_to_s3(content: str, metadata: DataIngestionMetadata) -> None:
    """
    Persists the given content to S3.

    Args:
        bucket_name (str): The s3 data bucket name.
        key (str): The s3 storage key.
        content (str): The raw XML responses from arXiv.
        metadata (DataIngestionMetadata): The data ingestion metadata.

    Raises:
        ValueError: If bucket name is not provided.
        ValueError: If key is not provided.
        ValueError: If content is not provided.
    """
    if not metadata.raw_data_bucket:
        logger.error("Bucket name is required", method=PERSIST_TO_S3)
        raise ValueError("Bucket name is required")

    if not metadata.raw_data_key:
        logger.error("Key is required", method=PERSIST_TO_S3)
        raise ValueError("Key is required")

    if not content:
        logger.error("Content is required", method=PERSIST_TO_S3)
        raise ValueError("Content is required")

    try:
        s3 = boto3.resource("s3")
        s3.Bucket(metadata.raw_data_bucket).put_object(Key=metadata.raw_data_key, Body=content)
        logger.info(
            "Persisting content to S3",
            method=PERSIST_TO_S3,
            bucket_name=metadata.raw_data_bucket,
            key=metadata.raw_data_key,
        )
    except Exception as e:
        logger.exception(
            "Failed to persist content to S3",
            method=PERSIST_TO_S3,
            bucket_name=metadata.raw_data_bucket,
            key=metadata.raw_data_key,
            error=str(e),
        )
        raise e
