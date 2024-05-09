import ast
import json
import os
from logging.config import dictConfig

import avro
import boto3
import defusedxml.ElementTree as ET
import requests
import structlog
from avro.io import validate
from confluent_kafka import Producer
from dotenv import load_dotenv
from neo4j import GraphDatabase
from requests.adapters import HTTPAdapter
from shared.database.s3_manager import S3Manager
from shared.models.data import Data
from shared.models.data_operation import DataOperation
from shared.models.data_source import DataSource
from shared.utils.constants import (
    AIRFLOW_DAGS_ENV_PATH,
    AIRFLOW_DATA_INTERVAL_START,
    AIRFLOW_RUN_ID,
    ARXIV_API_MAX_RETRIES,
    ARXIV_BASE_URL,
    ARXIV_RESEARCH_INGESTION_EVENT_SCHEMA_ENV,
    ARXIV_SETS,
    AWS_GLUE_REGISTRY_NAME,
    AWS_REGION,
    AWS_SECRETS_NEO4J_CREDENTIALS,
    AWS_SECRETS_NEO4J_PASSWORD,
    AWS_SECRETS_NEO4J_USERNAME,
    COMPLETED,
    DATA_ARXIV_SUMMARIES_INGESTION_COMPLETE_TOPIC,
    DATA_BUCKET,
    DATA_INGESTION_KEY_PREFIX,
    ENVIRONMENT_NAME,
    FETCH_FROM_ARXIV_TASK_VERSION,
    INGESTED_BY,
    INGESTION_EARLIEST_DATE,
    INGESTS,
    LOGGING_CONFIG,
    NEO4J_CONNECTION_RETRIES,
    NEO4J_CONNECTION_RETRIES_DEFAULT,
    NEO4J_PASSWORD,
    NEO4J_URI,
    NEO4J_USERNAME,
    OBTAINS_FROM,
    ORCHESTRATION_HOST_PRIVATE_IP,
    PROVIDES,
    RAW_DATA_KEYS,
    SCHEMA_DEFINITION,
    XML,
)
from shared.utils.utils import get_aws_secrets, get_storage_key
from urllib3.util.retry import Retry

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
load_dotenv(dotenv_path=os.getenv(AIRFLOW_DAGS_ENV_PATH))

TASK_NAME = "fetch_from_arxiv"


def run(**context: dict):
    try:
        logger.info(
            f"Running {TASK_NAME} task",
            task_name=TASK_NAME,
            date=context.get(AIRFLOW_DATA_INTERVAL_START),
            run_id=context.get(AIRFLOW_RUN_ID),
        )
        config = get_config(context)
        data = raw_data(config)
        results = store_data(config, data)
        data_nodes = store_metadata(config, data, results)
        logger.info(f"Completed {TASK_NAME} task", task_name=TASK_NAME, keys=", ".join(data.keys()))
        key_list = [x.get("key") for x in data.values()]
        context.get("ti").xcom_push(key=RAW_DATA_KEYS, value=key_list)
        publish_to_kafka(config, data_nodes)
    except Exception as e:
        logger.error(f"Failed to run {TASK_NAME} task", error=str(e), method=run.__name__, task_name=TASK_NAME)
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
            ARXIV_API_MAX_RETRIES: int(os.getenv(ARXIV_API_MAX_RETRIES)),
            ARXIV_BASE_URL: os.getenv(ARXIV_BASE_URL).strip(),
            ARXIV_RESEARCH_INGESTION_EVENT_SCHEMA_ENV: os.getenv(ARXIV_RESEARCH_INGESTION_EVENT_SCHEMA_ENV),
            ARXIV_SETS: ast.literal_eval(os.getenv(ARXIV_SETS)),
            AWS_GLUE_REGISTRY_NAME: os.getenv(AWS_GLUE_REGISTRY_NAME),
            AWS_REGION: os.getenv(AWS_REGION),
            DATA_ARXIV_SUMMARIES_INGESTION_COMPLETE_TOPIC: os.getenv(DATA_ARXIV_SUMMARIES_INGESTION_COMPLETE_TOPIC),
            DATA_BUCKET: os.getenv(DATA_BUCKET),
            DATA_INGESTION_KEY_PREFIX: os.getenv(DATA_INGESTION_KEY_PREFIX),
            ENVIRONMENT_NAME: os.getenv(ENVIRONMENT_NAME).strip(),
            FETCH_FROM_ARXIV_TASK_VERSION: os.getenv(FETCH_FROM_ARXIV_TASK_VERSION),
            INGESTION_EARLIEST_DATE: context.get("ti").xcom_pull(key=INGESTION_EARLIEST_DATE),
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
            not config.get(ARXIV_API_MAX_RETRIES)
            or not config.get(ARXIV_BASE_URL)
            or not config.get(ARXIV_RESEARCH_INGESTION_EVENT_SCHEMA_ENV)
            or not config.get(ARXIV_SETS)
            or not config.get(AWS_GLUE_REGISTRY_NAME)
            or not config.get(AWS_REGION)
            or not config.get(DATA_BUCKET)
            or not config.get(DATA_INGESTION_KEY_PREFIX)
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


def raw_data(config: dict) -> dict:
    """
    Fetches raw data from arXiv.

    Args:
        config (dict): The config.

    Returns:
        dict: The raw data.
    """
    fetched_xml_by_set = {}
    for set in config.get(ARXIV_SETS):
        storage_key = get_storage_key(config.get(DATA_INGESTION_KEY_PREFIX), set, XML)
        data = fetch_data(
            config.get(ARXIV_BASE_URL), config.get(INGESTION_EARLIEST_DATE), set, config.get(ARXIV_API_MAX_RETRIES)
        )
        fetched_xml_by_set[set] = {"key": storage_key, "data": data, "set": set}
    return fetched_xml_by_set


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

    if fetch_attempts == max_fetch_attempts and (resumption_token_element or len(full_xml_responses) == 0):
        logger.error("Reached maximum fetch attempts without completing data retrieval", method=fetch_data.__name__)
        raise RuntimeError("Reached maximum fetch attempts without completing data retrieval")

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
        total=3,
        backoff_factor=1,
        status_forcelist=[503],
        respect_retry_after_header=True,
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,
    )
    session.mount("http://", HTTPAdapter(max_retries=retries))
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session


def store_data(config: dict, raw_data: dict) -> dict:
    """
    Stores the raw data.

    Args:
        config (dict): The config.
        raw_data (dict): The raw data.

    Returns:
        results (dict): The results.
    """
    s3_manager = S3Manager(config.get(DATA_BUCKET), logger)
    sets_stored = []
    sets_failed = []
    for set, data in raw_data.items():
        try:
            s3_manager.upload_to_s3(data.get("key"), json.dumps(data.get("data")))
            sets_stored.append(set)
        except Exception as e:
            sets_failed.append(set)
            logger.error(
                "Failed to store data in S3",
                error=str(e),
                method=store_data.__name__,
                task_name=TASK_NAME,
                set=set,
            )
            raise e
    logger.info(
        "Stored data in S3",
        method=store_data.__name__,
        task_name=TASK_NAME,
        sets_stored=sets_stored,
        sets_failed=sets_failed,
    )
    return {"sets_stored": sets_stored, "sets_failed": sets_failed}


def store_metadata(config: dict, raw_data: dict, results: dict) -> dict:
    """
    Stores the metadata.

    Args:
        config (dict): The config.
        raw_data (dict): The raw data.
        results (dict): The results.

    Returns:
        data_nodes (dict): The data nodes created in the database.
    """
    if not config or not raw_data or not results:
        logger.error("Config, raw data, and results are required", method=store_metadata.__name__)
        raise ValueError("Config, raw data, and results are required")
    neo4j_driver = GraphDatabase.driver(
        config.get(NEO4J_URI), auth=(config.get(NEO4J_USERNAME), config.get(NEO4J_PASSWORD))
    )
    with neo4j_driver as driver:
        fetch_data_operation = DataOperation(
            driver, "Fetch arXiv Daily Summaries", TASK_NAME, config.get(FETCH_FROM_ARXIV_TASK_VERSION)
        )
        fetch_data_operation.create()
        data_nodes = {}
        for set, data in raw_data.items():
            try:
                data_source = get_data_source(config, driver)
                if not data_source:
                    logger.error("Failed to create data source", method=store_metadata.__name__, set=set)
                    raise ValueError("Failed to create data source")
                data_source.relate(
                    driver,
                    PROVIDES,
                    data_source.LABEL,
                    data_source.uuid,
                    fetch_data_operation.LABEL,
                    fetch_data_operation.uuid,
                    True,
                )
                fetch_data_operation.relate(
                    driver,
                    OBTAINS_FROM,
                    fetch_data_operation.LABEL,
                    fetch_data_operation.uuid,
                    data_source.LABEL,
                    data_source.uuid,
                    True,
                )
                data_node = Data(
                    driver, data.get("key"), XML, "raw arXiv daily summaries in XML", len(json.dumps(data.get("data")))
                )
                data_node.create()
                if not data_node:
                    logger.error("Failed to create data node", method=store_metadata.__name__, set=set)
                    raise RuntimeError("Failed to create data node")
                fetch_data_operation.relate(
                    driver,
                    INGESTS,
                    fetch_data_operation.LABEL,
                    fetch_data_operation.uuid,
                    data_node.LABEL,
                    data_node.uuid,
                )
                data_node.relate(
                    driver,
                    INGESTED_BY,
                    data_node.LABEL,
                    data_node.uuid,
                    fetch_data_operation.LABEL,
                    fetch_data_operation.uuid,
                )
                data_nodes.update({set: data_node})
            except Exception as e:
                logger.error(
                    "Failed to store metadata",
                    error=str(e),
                    method=store_metadata.__name__,
                    set=set,
                    task_name=TASK_NAME,
                )
                raise e
        logger.info("Stored metadata", method=store_metadata.__name__, task_name=TASK_NAME)
        return data_nodes


def get_data_source(config: dict, driver: GraphDatabase) -> DataSource:
    """
    Gets the data source.

    Args:
        config (dict): The config.
        driver (GraphDatabase): The driver.

    Returns:
        Data: The data source.
    """
    driver.verify_connectivity()
    data_source = None
    try:
        data_source = DataSource.find(driver, config.get(ARXIV_BASE_URL))
    except Exception as e:
        logger.error("Failed to find arXiv data source", method=store_metadata.__name__, error=str(e))
    if not data_source:
        data_source = DataSource(driver, config.get(ARXIV_BASE_URL), "arXiv", "Preprint server")
        data_source.create()
    return data_source


def publish_to_kafka(config: dict, data_nodes: list):
    glue_client = boto3.client("glue", region_name=config.get(AWS_REGION))
    schema_response = glue_client.get_schema_version(
        SchemaId={
            "RegistryName": config.get(AWS_GLUE_REGISTRY_NAME),
            "SchemaName": config.get(ARXIV_RESEARCH_INGESTION_EVENT_SCHEMA_ENV),
        },
        SchemaVersionNumber={"LatestVersion": True},
    )
    schema = avro.schema.parse(schema_response.get(SCHEMA_DEFINITION))

    producer = Producer({"bootstrap.servers": f"{os.getenv(ORCHESTRATION_HOST_PRIVATE_IP)}:9092"})

    for set, data_node in data_nodes.items():
        try:
            data = {
                "status": COMPLETED,
                "s3_key": data_node.url,
                "from_date": config.get(INGESTION_EARLIEST_DATE),
                "arxiv_set": set,
                "raw_data_uuid": data_node.uuid,
            }
            if not validate(schema, data):
                raise ValueError("Data does not match the schema")

            producer.produce(DATA_ARXIV_SUMMARIES_INGESTION_COMPLETE_TOPIC, json.dumps(data))
        except Exception as e:
            logger.error(
                "Failed to validate data against schema",
                error=str(e),
                method=publish_to_kafka.__name__,
                data=data,
                task_name=TASK_NAME,
            )
            raise e

    producer.flush()
