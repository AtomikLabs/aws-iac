import json
import os
import uuid
from logging.config import dictConfig

import defusedxml.ElementTree as ET
import structlog
from neo4j import GraphDatabase
from shared.database.s3_manager import S3Manager
from shared.models.data import Data
from shared.models.data_operation import DataOperation
from shared.utils.constants import (
    CREATED_BY,
    CREATES,
    CS_CATEGORIES_INVERTED,
    DATA_BUCKET,
    ENVIRONMENT_NAME,
    ETL_KEY_PREFIX,
    INTERNAL_SERVER_ERROR,
    LOGGING_CONFIG,
    NEO4J_PASSWORD,
    NEO4J_URI,
    NEO4J_USERNAME,
    PARSED_BY,
    PARSES,
    RAW_DATA_KEYS,
    SCHEMA,
    SERVICE_NAME,
    SERVICE_VERSION,
)
from shared.utils.utils import get_storage_key_date, set_neo4j_env_vars

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


def run(**context: dict):
    try:
        config = get_config()
        schema = context.get("ti").xcom_pull(task_ids="fetch_from_arxiv_task", key=SCHEMA)
        print(schema)
        s3_manager = S3Manager(os.getenv(DATA_BUCKET), logger)
        create_json_data(config, s3_manager, schema.get("s3_key"))
    except Exception as e:
        logger.error(e)
        return {"statusCode": 500, "body": INTERNAL_SERVER_ERROR, "error": str(e)}
    return {"statusCode": 200, "body": "Success"}


def create_json_data(config: dict, s3_manager: S3Manager, key: str) -> dict:
    try:
        xml_data = json.loads(s3_manager.load(key))
        extracted_data = {"records": []}
        success = True
        for xml in xml_data:
            extracted_records = parse_xml_data(xml)
            extracted_data["records"].extend(extracted_records)
        with GraphDatabase.driver(
            config.get(NEO4J_URI), auth=(config.get(NEO4J_USERNAME), config.get(NEO4J_PASSWORD))
        ) as driver:
            raw_data = None
            try:
                raw_data = Data.find(driver, key)
                if not raw_data:
                    message = f"Failed to find raw data with key: {key}"
                    logger.error(message, method=run.__name__)
                    raise RuntimeError(message)
            except Exception as e:
                logger.error("Failed to find raw data source", method=run.__name__, error=str(e))
                raise e
            data_operation = DataOperation(driver, "Parse arXiv research summaries", "parse_arxiv_summaries", "1.0.0")
            data_operation.create()
            if not data_operation:
                message = "Failed to create DataOperation"
                logger.error(message, method=run.__name__)
                raise RuntimeError(message)
            parsed_data = None
            try:
                content_str = json.dumps(extracted_data["records"])
                output_key = get_output_key(config)
                s3_manager.upload_to_s3(output_key, content_str)
                parsed_data = Data(driver, output_key, "json", "parsed arXiv summaries", len(content_str))
                parsed_data.create()
                if not parsed_data:
                    message = f"Failed to create parsed data with key: {output_key}"
                    logger.error(message, method=run.__name__)
                    raise RuntimeError(message)
                data_operation.relate(
                    driver, PARSES, data_operation.LABEL, data_operation.uuid, raw_data.LABEL, raw_data.uuid, True
                )
                data_operation.relate(
                    driver,
                    PARSED_BY,
                    raw_data.LABEL,
                    raw_data.uuid,
                    data_operation.LABEL,
                    data_operation.uuid,
                    True,
                )
                data_operation.relate(
                    driver,
                    CREATES,
                    data_operation.LABEL,
                    data_operation.uuid,
                    parsed_data.LABEL,
                    parsed_data.uuid,
                    True,
                )
                data_operation.relate(
                    driver,
                    CREATED_BY,
                    parsed_data.LABEL,
                    parsed_data.uuid,
                    data_operation.LABEL,
                    data_operation.uuid,
                    True,
                )
            except Exception as e:
                logger.error(
                    "Failed to create parsed data",
                    method=run.__name__,
                    key=output_key if output_key else "",
                    error=str(e),
                )
                success = False
        logger.info("Finished parsing arXiv daily summaries", method=run.__name__)
        return (
            {"statusCode": 200, "body": "Success"} if success else {"statusCode": 500, "body": "Failed to parse data"}
        )
    except Exception as e:
        logger.error(e)
        return {"statusCode": 500, "body": INTERNAL_SERVER_ERROR, "error": str(e)}


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
            ENVIRONMENT_NAME: os.environ[ENVIRONMENT_NAME],
            ETL_KEY_PREFIX: os.environ[ETL_KEY_PREFIX],
            SERVICE_NAME: os.environ[SERVICE_NAME],
            SERVICE_VERSION: os.environ[SERVICE_VERSION],
        }
        config = set_neo4j_env_vars(config)
        logger.debug("Config", method=get_config.__name__, config=config)
    except KeyError as e:
        logger.error("Missing environment variable", method=get_config.__name__, error=str(e))
        raise e
    logger.debug("Config", method=get_config.__name__, config=config)
    return config


def parse_xml_data(xml_data: str) -> list:
    """
    Parses raw arXiv XML data into a json format for further processing.
    Returns a flat list of objects for each record in the XML with a selected
    subset of fields.

    Args:
        xml_data (str): Raw arXiv XML data.

    Returns:
        list: Parsed data.
    """
    extracted_data_chunk = []
    logger.info("Parsing XML data", method=parse_xml_data.__name__, data_length=len(xml_data))
    try:
        root = ET.fromstring(xml_data)
        ns = {"oai": "http://www.openarchives.org/OAI/2.0/", "dc": "http://purl.org/dc/elements/1.1/"}

        for record in root.findall(".//oai:record", ns):
            date_elements = record.findall(".//dc:date", ns)
            if len(date_elements) != 1:
                continue

            identifier = record.find(".//oai:identifier", ns).text
            abstract_url = record.find(".//dc:identifier", ns).text

            creators_elements = record.findall(".//dc:creator", ns)
            authors = []
            for creator in creators_elements:
                name_parts = creator.text.split(", ", 1)
                last_name = name_parts[0]
                first_name = name_parts[1] if len(name_parts) > 1 else ""
                authors.append({"last_name": last_name, "first_name": first_name})

            # Find all subjects
            subjects_elements = record.findall(".//dc:subject", ns)
            categories = [CS_CATEGORIES_INVERTED.get(subject.text, "") for subject in subjects_elements]
            # Remove empty strings
            categories = list(filter(None, categories))
            if not categories:
                categories.append("NULL")

            abstract = record.find(".//dc:description", ns).text.replace("\n", " ")
            title = record.find(".//dc:title", ns).text.replace("\n", "")
            date = date_elements[0].text
            group = "cs"

            extracted_data_chunk.append(
                {
                    "identifier": identifier,
                    "abstract_url": abstract_url,
                    "authors": authors,
                    "categories": categories,
                    "abstract": abstract,
                    "title": title,
                    "date": date,
                    "group": group,
                }
            )
    except ET.ParseError as e:
        logger.error("Failed to parse XML data", method=parse_xml_data.__name__, error=str(e))

    logger.info("Finished parsing XML data", method=parse_xml_data.__name__, data_length=len(extracted_data_chunk))
    return extracted_data_chunk


def get_output_key(config) -> str:
    """
    Gets the output key for parsed arxiv summaries.

    Returns:
        str: The output key.
    """
    key_date = get_storage_key_date()
    return f"{config[ETL_KEY_PREFIX]}/{str(uuid.uuid4())}-parsed_arxiv_summaries-{key_date}.json"


def chunker(seq: list, size: int) -> list:
    """
    Chunks a list into smaller lists.

    Args:
        seq (list): The list to chunk.
        size (int): The size of each chunk.

    Returns:
        list: The chunked list.
    """
    return (seq[pos : pos + size] for pos in range(0, len(seq), size))
