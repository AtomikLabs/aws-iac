import json
import os
import urllib.parse
from datetime import datetime

import defusedxml.ElementTree as ET
import pytz
import structlog
from arxiv_constants import CS_CATEGORIES_INVERTED
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

# ENVIRONMENT VARIABLES
APP_NAME = "APP_NAME"
DATA_BUCKET = "DATA_BUCKET"
ENVIRONMENT_NAME = "ENVIRONMENT"
ETL_KEY_PREFIX = "ETL_KEY_PREFIX"
SERVICE_NAME = "SERVICE_NAME"
SERVICE_VERSION = "SERVICE_VERSION"

# LOGGING CONSTANTS
# TODO: Centralize error messages
INTERNAL_SERVER_ERROR = "Internal server error"
NO_REGION_SPECIFIED = "No region specified"
PARSE_DATA = "parse_arxiv_summaries.lambda_handler.fetch_data"
GET_CONFIG = "parse_arxiv_summaries.lambda_handler.get_config"
LAMBDA_HANDLER = "parse_arxiv_summaries.lambda_handler"
LOAD_XML_FROM_S3 = "parse_arxiv_summaries.lambda_handler.load_xml_from_s3"
LOG_INITIAL_INFO = "parse_arxiv_summaries.lambda_handler.log_initial_info"
PERSIST_TO_S3 = "parse_arxiv_summaries.lambda_handler.persist_to_s3"

S3_KEY_DATE_FORMAT = "%Y-%m-%dT%H-%M-%S"


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
        xml_data = json.loads(storage_manager.load(key))
        extracted_data = {"records": []}
        for xml in xml_data:
            extracted_records = parse_xml_data(xml)
            extracted_data["records"].extend(extracted_records)
        content_str = json.dumps(extracted_data)
        output_key = get_output_key(config)
        storage_manager.upload_to_s3(output_key, content_str)
        logger.info("Finished parsing arXiv daily summaries")
        return {"statusCode": 200, "body": "Success"}

    except Exception as e:
        logger.error(e)
        return {"statusCode": 500, "body": INTERNAL_SERVER_ERROR}


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
            primary_category = categories[0] if categories else ""

            abstract = record.find(".//dc:description", ns).text.replace("\n", " ")
            title = record.find(".//dc:title", ns).text.replace("\n", "")
            date = date_elements[0].text
            group = "cs"

            extracted_data_chunk.append(
                {
                    "identifier": identifier,
                    "abstract_url": abstract_url,
                    "authors": authors,
                    "primary_category": primary_category,
                    "categories": categories,  # All categories
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
    storage_date = datetime.now().astimezone(pytz.timezone("US/Pacific"))
    key_date = storage_date.strftime(S3_KEY_DATE_FORMAT)
    return f"{config[ETL_KEY_PREFIX]}/parsed_arxiv_summaries-{key_date}.json"
