import json
import os
import urllib.parse
from typing import Dict, List

import structlog
from constants import DATA_BUCKET, NEO4J_PASSWORD, NEO4J_URI, NEO4J_USERNAME, SERVICE_NAME, SERVICE_VERSION
from models.arxiv_category import ArxivCategory
from models.arxiv_record import ArxivRecord
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
        bucket_name = event["Records"][0]["s3"]["bucket"]["name"]
        key = urllib.parse.unquote_plus(event["Records"][0]["s3"]["object"]["key"], encoding="utf-8")
        config = get_config()
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
        store_records(json_data.get("records"), bucket_name, key, config)
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
    logger.debug("Config", method=get_config.__name__, config=config)
    return config


def store_records(records: List[Dict], bucket_name: str, key: str, config: dict) -> Dict:
    """
    Stores arxiv research summary records in the neo4j database.

    Args:
        records (List[Dict]): The arXiv records to store.
        bucket_name (str): The S3 bucket name for the parsed arXiv records.
        key (str): The S3 key for the parsed arXiv records.
        config (dict): The configuration for the service.

    Returns:
        Dict: The stored and failed records for further processing.
    """
    if not records or not isinstance(records, list):
        logger.error(
            "Records must be present and be a list of dict.",
            method=store_records.__name__,
            records_type=type(records),
            records=records,
        )
        raise ValueError("Records must be present and be a list of dict.")
    if not bucket_name or not isinstance(bucket_name, str):
        logger.error(
            "Bucket name for parsed records must be present and be a string.",
            method=store_records.__name__,
            bucket_name_type=type(bucket_name),
            bucket_name=bucket_name,
        )
        raise ValueError("Bucket name must be present and be a string.")
    service_name = config.get(SERVICE_NAME)
    service_version = config.get(SERVICE_VERSION)
    neo4j_uri = config.get(NEO4J_URI)
    neo4j_username = config.get(NEO4J_USERNAME)
    neo4j_password = config.get(NEO4J_PASSWORD)
    if (
        not key
        or not isinstance(key, str)
        or not service_name
        or not isinstance(service_name, str)
        or not service_version
        or not isinstance(service_version, str)
    ):
        logger.error(
            "Key, service name, and service version must be present and be strings.",
            method=store_records.__name__,
            key_type=type(key),
            key=key,
            service_name_type=type(service_name),
            service_name=service_name,
            service_version_type=type(service_version),
            service_version=service_version,
        )
        raise ValueError(
            "Key, service name, and service version must be present \
                         and be strings."
        )
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
            with Neo4jDatabase(neo4j_uri, neo4j_username, neo4j_password).driver() as driver:
                for record in well_formed_records[:2]:
                    try:
                        arxiv_record = ArxivRecord(
                            driver=driver,
                            arxiv_id=record.get("identifier"),
                            title=record.get("title"),
                            date=record.get("date"),
                        )
                        arxiv_category = ArxivCategory.find(
                            driver, record.get("primary_category") if record.get("primary_category") else "NULL"
                        )
                        if not arxiv_category:
                            # TODO: Monitoring alert here
                            logger.warn(
                                "Failed to find ArxivCategory",
                                method=store_records.__name__,
                                arxiv_category=record.get("primary_category").upper(),
                            )
                            raise RuntimeError("Failed to find ArxivCategory")
                        arxiv_record.create()
                        arxiv_record.relate(
                            driver,
                            "BELONGS_TO",
                            ArxivRecord.LABEL,
                            arxiv_record.uuid,
                            ArxivCategory.LABEL,
                            arxiv_category.uuid,
                            True,
                        )
                    except Exception as e:
                        logger.error(
                            "Error during record and relationship creation",
                            method=store_records.__name__,
                            record=record,
                        )

            logger.info("Stored records", method=store_records.__name__, num_records=len(well_formed_records))
            # TODO: set alerting for malformed records
            logger.info(
                "Malfored records found",
                method=store_records.__name__,
                num_records=len(malformed_records),
                malformed_records=malformed_records,
            )
            if total != len(well_formed_records) + len(malformed_records):
                # set alerting for unprocessed records
                logger.error(
                    "Some records were not processed",
                    method=store_records.__name__,
                    num_records=len(records),
                    num_well_formed_records=len(well_formed_records),
                    num_malformed_records=len(malformed_records),
                )
        return {"stored": well_formed_records, "failed": malformed_records}
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
