import json
import os
from datetime import timedelta

import defusedxml.ElementTree as ET
import requests
import structlog
import utils
from constants import (
    APP_NAME,
    ARXIV_BASE_URL,
    ARXIV_SUMMARY_SET,
    DATA_BUCKET,
    DATA_INGESTION_KEY_PREFIX,
    ENVIRONMENT_NAME,
    INGESTED_BY,
    INGESTS,
    MAX_RETRIES,
    NEO4J_PASSWORD,
    NEO4J_URI,
    NEO4J_USERNAME,
    OBTAINS_FROM,
    PROVIDES,
    SERVICE_NAME,
    SERVICE_VERSION,
)
from models.data import Data
from models.data_operation import DataOperation
from models.data_source import DataSource
from neo4j import GraphDatabase
from requests.adapters import HTTPAdapter
from storage_manager import StorageManager
from urllib3.util.retry import Retry

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
DAY_SPAN = 2


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
            method=lambda_handler.__name__,
            service_name=config[SERVICE_NAME],
            service_version=config[SERVICE_VERSION],
        )
        date_obtained = utils.get_storage_key_datetime()
        today = date_obtained.date()
        earliest = today - timedelta(days=DAY_SPAN)

        xml_data_list = fetch_data(
            config.get(ARXIV_BASE_URL), earliest, config.get(ARXIV_SUMMARY_SET), config.get(MAX_RETRIES)
        )

        raw_data_key = get_storage_key(config)
        content_str = json.dumps(xml_data_list)
        storage_manager = StorageManager(config.get(DATA_BUCKET), logger)
        storage_manager.upload_to_s3(raw_data_key, content_str)
        with GraphDatabase.driver(
            config.get(NEO4J_URI), auth=(config.get(NEO4J_USERNAME), config.get(NEO4J_PASSWORD))
        ) as driver:
            data_source = None
            try:
                data_source = DataSource.find(driver, config.get(ARXIV_BASE_URL))
            except Exception as e:
                logger.error("Failed to find arXiv data source", method=lambda_handler.__name__, error=str(e))
            if not data_source:
                data_source = DataSource(driver, config.get(ARXIV_BASE_URL), "arXiv", "Preprint server")
                data_source.create()
            data = None
            try:
                data = Data(driver, raw_data_key, "xml", "raw arXiv daily summaries", len(content_str))
                data.create()
                if not data:
                    message = f"Failed to create data with key: {raw_data_key}"
                    logger.error(message, method=lambda_handler.__name__)
                    raise RuntimeError(message)
            except Exception as e:
                logger.error("Failed to create data", method=lambda_handler.__name__, error=str(e))
                raise e
            data_operation = DataOperation(
                driver, "Fetch arXiv daily summaries", config.get(SERVICE_NAME), config.get(SERVICE_VERSION)
            )
            data_operation.create()
            if data_operation:
                data_operation.relate(
                    driver,
                    PROVIDES,
                    data_source.LABEL,
                    data_source.uuid,
                    data_operation.LABEL,
                    data_operation.uuid,
                    True,
                )
                data_operation.relate(
                    driver,
                    OBTAINS_FROM,
                    data_operation.LABEL,
                    data_operation.uuid,
                    data_source.LABEL,
                    data_source.uuid,
                    True,
                )
                data_operation.relate(
                    driver, INGESTS, data_operation.LABEL, data_operation.uuid, data.LABEL, data.uuid, True
                )
                data_operation.relate(
                    driver, INGESTED_BY, data.LABEL, data.uuid, data_operation.LABEL, data_operation.uuid, True
                )
            else:
                message = f"Failed to create data operation with name: {data_operation.name}"
                logger.error(message, method=lambda_handler.__name__)
                raise RuntimeError(message)
        logger.info("Fetching arXiv summaries succeeded", method=lambda_handler.__name__, status=200, body="Success")
        return {"statusCode": 200, "body": json.dumps({"message": "Success"})}
    except Exception as e:
        logger.exception(
            "Fetching arXiv daily summaries failed",
            method=lambda_handler.__name__,
            status=500,
            body="Internal Server Error",
            error=str(e),
        )
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Internal Server Error"}),
            "error": str(e),
            "event": event,
        }


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
        logger.debug("Config", method=get_config.__name__, config=config)
    except KeyError as e:
        logger.error("Missing environment variable", method=get_config.__name__, error=str(e))
        raise e

    return config


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
        logger.error(error_msg, method=fetch_data.__name__)
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
        logger.exception("Error occurred while fetching data from arXiv", method=fetch_data.__name__, error=str(e))
        raise

    if fetch_attempts == max_fetch_attempts:
        logger.warning("Reached maximum fetch attempts without completing data retrieval", method=fetch_data.__name__)

    logger.info(
        "Fetched data from arXiv successfully", method=fetch_data.__name__, num_xml_responses=len(full_xml_responses)
    )
    return full_xml_responses


def configure_request_retries() -> requests.Session:
    """
    Configures request retries.

    Returns:
        requests.Session: The session.
    """
    logger.debug("Configuring request retries", method=configure_request_retries.__name__)
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
        logger.error("Config is required", method=get_storage_key.__name__)
        raise ValueError("Config is required")
    key_date = utils.get_storage_key_date()
    key = f"{config.get(DATA_INGESTION_KEY_PREFIX)}/arxiv-{key_date}.json"
    logger.info("Storage key", method=get_storage_key.__name__, key=key)
    return key
