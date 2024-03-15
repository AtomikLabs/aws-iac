import json
import os
import sys
import time
from datetime import datetime, timedelta

import defusedxml.ElementTree as ET
import requests
import structlog
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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
# TODO: Make these constants configurable
BACKOFF_TIMES = [30, 120]
DAY_SPAN = 5

# ENVIRONMENT VARIABLES
APP_NAME = "APP_NAME"
ARXIV_BASE_URL = "ARXIV_BASE_URL"
ARXIV_SUMMARY_SET = "ARXIV_SUMMARY_SET"
DATA_BUCKET = "DATA_BUCKET"
DATA_CATALOG_DB_NAME = "DATA_CATALOG_DB_NAME"
DATA_INGESTION_KEY_PREFIX = "DATA_INGESTION_KEY_PREFIX"
ENVIRONMENT_NAME = "ENVIRONMENT"
MAX_RETRIES = "MAX_RETRIES"
NEO4J_PASSWORD = "NEO4J_PASSWORD"
NEO4J_URI = "NEO4J_URI"
NEO4J_USERNAME = "NEO4J_USERNAME"
SERVICE_NAME = "SERVICE_NAME"
SERVICE_VERSION = "SERVICE_VERSION"

# LOGGING CONSTANTS
FETCH_DATA = "fetch_daily_summaries.lambda_handler.fetch_data"
GET_CONFIG = "fetch_daily_summaries.lambda_handler.get_config"
GET_EARLIEST_DATE = "fetch_daily_summaries.lambda_handler.get_earliest_date"
GET_STORAGE_KEY = "fetch_daily_summaries.lambda_handler.get_storage_key"
LAMBDA_HANDLER = "fetch_daily_summaries.lambda_handler"
LAMBDA_NAME = "fetch_daily_summaries"
LOG_INITIAL_INFO = "fetch_daily_summaries.lambda_handler.log_initial_info"
PERSIST_TO_S3 = "fetch_daily_summaries.lambda_handler.persist_to_s3"

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f%z"
S3_KEY_DATE_FORMAT = "%Y-%m-%dT%H-%M-%S"


def lambda_handler(event: dict, context) -> dict:
    """
    The main entry point for the Lambda function.

    Args:
        event (dict): The event data from AWS.
        context: The context data.

    Returns:
        dict: A dict with the status code and body.
    """
    try:
        log_initial_info(event)

        config = get_config()

        logger.info(
            "Fetching arXiv daily summaries",
            method=LAMBDA_HANDLER,
            service_name=config[SERVICE_NAME],
            service_version=config[SERVICE_VERSION],
        )

        today = datetime.today().date()
        earliest = today - timedelta(days=DAY_SPAN)

        xml_data_list = fetch_data(
            config.get(ARXIV_BASE_URL), earliest, config.get(ARXIV_SUMMARY_SET), config.get(MAX_RETRIES)
        )

        raw_data_key = get_storage_key(config)
        content_str = json.dumps(xml_data_list)
        storage_manager = StorageManager(config.get(DATA_BUCKET), logger)
        storage_manager.upload_to_s3(raw_data_key, content_str)
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
        return {"statusCode": 500, "body": json.dumps({"message": "Internal Server Error"})}


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


def get_config() -> dict:
    """
    Gets the config from the environment variables.

    Returns:
        dict: The config.
    """
    try:
        config = {
            APP_NAME: os.environ[APP_NAME],
            ARXIV_BASE_URL: os.environ[ARXIV_BASE_URL],
            ARXIV_SUMMARY_SET: os.environ[ARXIV_SUMMARY_SET],
            DATA_BUCKET: os.environ[DATA_BUCKET],
            DATA_INGESTION_KEY_PREFIX: os.environ[DATA_INGESTION_KEY_PREFIX],
            ENVIRONMENT_NAME: os.environ[ENVIRONMENT_NAME],
            MAX_RETRIES: int(os.environ[MAX_RETRIES]),
            NEO4J_PASSWORD: os.environ[NEO4J_PASSWORD],
            NEO4J_URI: os.environ[NEO4J_URI],
            NEO4J_USERNAME: os.environ[NEO4J_USERNAME],
            SERVICE_NAME: os.environ[SERVICE_NAME],
            SERVICE_VERSION: os.environ[SERVICE_VERSION],
        }
        logger.debug("Config", method=GET_CONFIG, config=config)
    except KeyError as e:
        logger.error("Missing environment variable", method=GET_CONFIG, error=str(e))
        raise e

    return config


def set_data_source():
    """
    Sets the data source.
    """


def fetch_data(base_url: str, from_date: str, set: str, max_fetches: int) -> list:
    """
    Fetches data from arXiv.

    Args:
        base_url (str): The base URL.
        from_date (str): The from date.
        set (str): The set.
        max_fetches (int): The maximum number of fetches.

    Returns:
        list: A list of XML data.

    Raises:
        ValueError: If base_url, from_date, or set are not provided.
    """
    if not base_url or not from_date or not set:
        error_msg = "Base URL, from date, and set are required"
        logger.error(error_msg, method=FETCH_DATA)
        raise ValueError(error_msg)

    session = configure_request_retries()

    params = {"verb": "ListRecords", "set": set, "metadataPrefix": "oai_dc", "from": from_date}
    full_xml_responses = []
    fetch_attempts = 0
    max_fetch_attempts = max_fetches

    try:
        while fetch_attempts < max_fetch_attempts:
            response = session.get(base_url, params=params, timeout=(10, 30))
            response.raise_for_status()
            full_xml_responses.append(response.text)

            root = ET.fromstring(response.content)
            resumption_token_element = root.find(".//{http://www.openarchives.org/OAI/2.0/}resumptionToken")
            if resumption_token_element is not None and resumption_token_element.text:
                params = {"verb": "ListRecords", "resumptionToken": resumption_token_element.text}
                fetch_attempts += 1
            else:
                break
    except requests.exceptions.RequestException as e:
        logger.exception("Error occurred while fetching data from arXiv", method=FETCH_DATA, error=str(e))
        raise

    if fetch_attempts == max_fetch_attempts:
        logger.warning("Reached maximum fetch attempts without completing data retrieval", method=FETCH_DATA)

    logger.info("Fetched data from arXiv successfully", method=FETCH_DATA, num_xml_responses=len(full_xml_responses))
    return full_xml_responses


def configure_request_retries() -> requests.Session:
    """
    Configures request retries.

    Returns:
        requests.Session: The session.
    """
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[503],
        respect_retry_after_header=True,
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,
    )
    session.mount("http://", HTTPAdapter(max_retries=retries))
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session


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
    Gets the storage key for the S3 bucket to store the fetched data.

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

    key_date = time.strftime(S3_KEY_DATE_FORMAT)
    key = f"{config.get(DATA_INGESTION_KEY_PREFIX)}/{key_date}.json"
    logger.info("Storage key", method=GET_STORAGE_KEY, key=key)
    return key
