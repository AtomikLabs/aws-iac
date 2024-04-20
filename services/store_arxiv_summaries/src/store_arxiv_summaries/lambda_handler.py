import json
import logging
import os
import urllib.parse
import uuid
from typing import Dict, List, Tuple

import structlog
from constants import (
    AUTHORED_BY,
    AUTHORS,
    CATEGORIZED_BY,
    CATEGORIZES,
    CREATED_BY,
    CREATES,
    DATA_BUCKET,
    LOADED_BY,
    LOADS,
    NEO4J_PASSWORD,
    NEO4J_URI,
    NEO4J_USERNAME,
    PRIMARILY_CATEGORIZED_BY,
    RECORDS_PREFIX,
    SERVICE_NAME,
    SERVICE_VERSION,
    SUMMARIZED_BY,
    SUMMARIZES,
)
from models.abstract import Abstract
from models.arxiv_category import ArxivCategory
from models.arxiv_record import ArxivRecord
from models.author import Author
from models.base_model import BaseModel
from models.data import Data
from models.data_operation import DataOperation
from neo4j import Driver, GraphDatabase
from storage_manager import StorageManager
from utils import get_storage_key_datetime

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
        store_records(json_data["records"], bucket_name, key, config, storage_manager)
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


def store_records(
    records: List[Dict], bucket_name: str, key: str, config: dict, storage_manager: StorageManager
) -> Dict:
    """
    Stores arxiv research summary records in the neo4j database.

    Args:
        records (List[Dict]): The arXiv records to store.
        bucket_name (str): The S3 bucket name for the parsed arXiv records.
        key (str): The S3 key for the parsed arXiv records.
        config (dict): The configuration for the service.
        storage_manager (StorageManager): The storage manager.

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
    malformed_records = []
    well_formed_records = []
    try:
        with GraphDatabase.driver(
            config.get(NEO4J_URI), auth=(config.get(NEO4J_USERNAME), config.get(NEO4J_PASSWORD))
        ) as driver:
            parsed_data = parsed_data_node(driver, key)
            loads_dop = loads_dop_node(
                driver,
                "Load parsed arXiv records",
                config.get(SERVICE_NAME),
                config.get(SERVICE_VERSION),
                parsed_data,
            )

            categories = {c.code: c for c in ArxivCategory.find_all(driver)}
            arxiv_records, authors, abstracts, relationships, malformed_records = generate_csv_data(
                records, loads_dop.uuid, bucket_name, config.get(RECORDS_PREFIX), categories
            )
            with open("/tmp/arxiv_records.csv", "w") as f:
                f.writelines(arxiv_records)
            with open("/tmp/authors.csv", "w") as f:
                f.writelines(authors)
            with open("/tmp/abstracts.csv", "w") as f:
                f.writelines(abstracts)
            with open("/tmp/relationships.csv", "w") as f:
                f.writelines(relationships)
            storage_manager.upload_to_s3(f"{config.get(RECORDS_PREFIX)}/moo/arxiv_records.csv", "".join(arxiv_records))
            storage_manager.upload_to_s3(f"{config.get(RECORDS_PREFIX)}/moo/authors.csv", "".join(authors))
            storage_manager.upload_to_s3(f"{config.get(RECORDS_PREFIX)}/moo/abstracts.csv", "".join(abstracts))
            storage_manager.upload_to_s3(f"{config.get(RECORDS_PREFIX)}/moo/relationships.csv", "".join(relationships))
            with open("/tmp/arxiv_records.csv", "r") as f:
                lines = f.readlines()
                print(lines[:5])
            with open("/tmp/authors.csv", "r") as f:
                lines = f.readlines()
                print(lines[:5])
            with open("/tmp/abstracts.csv", "r") as f:
                lines = f.readlines()
                print(lines[:5])
            with open("/tmp/relationships.csv", "r") as f:
                lines = f.readlines()
                print(lines[:5])

    except Exception as e:
        logger.error("An error occurred", method=store_records.__name__, error=str(e))
        raise e
    finally:
        logger.info(
            "Finished storing records",
            method=store_records.__name__,
            num_malformed_records=len(malformed_records),
            num_well_formed_records=len(well_formed_records),
        )


def parsed_data_node(driver: Driver, key: str) -> Data:
    """
    Creates a parsed data node in the graph.

    Args:
        driver (Driver): The neo4j driver.
        key (str): The key for the parsed data.

    Returns:
        Data: The parsed data node.

    Raises:
        RuntimeError: If the parsed data node cannot be found.
    """
    parsed_data = Data.find(driver, key)
    if not parsed_data:
        message = f"Failed to find parsed data with key: {key}"
        logger.error(message, method=parsed_data_node.__name__)
        raise RuntimeError(message)
    return parsed_data


def loads_dop_node(
    driver: Driver, description: str, method_name: str, method_version: str, parsed_data: Data
) -> DataOperation:
    """
    Creates a data operation node for loading the parsed data.

    Args:
        driver (Driver): The neo4j driver.
        description (str): The description of the data operation.
        method_name (str): The name of the method.
        method_version (str): The version of the method.
        parsed_data (Data): The parsed data node.

    Returns:
        DataOperation: The data operation node.
    """
    loads_dop = DataOperation(driver, description, method_name, method_version)
    loads_dop.create()
    if not loads_dop:
        message = "Failed to create DataOperation"
        logger.error(message, method=loads_dop_node.__name__)
        raise RuntimeError(message)
    parsed_data.relate(
        driver,
        LOADS,
        DataOperation.LABEL,
        loads_dop.uuid,
        Data.LABEL,
        parsed_data.uuid,
        True,
    )
    loads_dop.relate(
        driver,
        LOADED_BY,
        Data.LABEL,
        parsed_data.uuid,
        DataOperation.LABEL,
        loads_dop.uuid,
        True,
    )
    return loads_dop


def generate_csv_data(
    records: List[Dict], loads_dop_uuid: str, bucket: str, records_prefix: str, categories: dict
) -> Tuple[List[str], List[str], List[str], List[str]]:
    """
    Generates the CSV data for the arXiv records.

    Args:
        records (List[Dict]): The arXiv records.
        loads_dop_uuid (str): The UUID of the data operation node for loading the parsed data.
        bucket (str): The S3 bucket name for storing arXiv records.
        records_prefix (str): The prefix for the records.
        categories (dict): The arXiv categories from the graph.

    Returns:
        Tuple[List[str], List[str], List[str], List[str], List[str]]: The arXiv records, authors, abstracts,
        relationships, and malformed records as csvs.
    """

    abstracts = [Abstract.FIELDS_CSV]
    arxiv_records = [ArxivRecord.FIELDS_CSV]
    authors = [Author.FIELDS_CSV]
    relationships = [BaseModel.RELATIONSHIP_CSV]

    malformed_records = []
    required_fields = ["identifier", "title", "authors", "group", "abstract", "date", "abstract_url"]
    for record in records:
        try:
            if not all(field in record for field in required_fields):
                malformed_records.append(record)
                continue

            rec = arxiv_record_factory(record)
            rec_uuid = rec.split(",")[-1].strip()
            arxiv_records.append(rec)

            au_list = author_factory(record)
            for author in au_list:
                authors.append(author)

            ab = abstract_factory(record, bucket, records_prefix)
            abstracts.append(ab)
            ab_uuid = ab.split(",")[-1].strip()

            rels = []

            rels.append(relationship_factory(CREATES, DataOperation.LABEL, loads_dop_uuid, ArxivRecord.LABEL, rec_uuid))
            rels.append(
                relationship_factory(CREATED_BY, ArxivRecord.LABEL, rec_uuid, DataOperation.LABEL, loads_dop_uuid)
            )

            for author in au_list:
                au_id = author.split(",")[-1].strip()
                rels.append(relationship_factory(AUTHORS, Author.LABEL, au_id, ArxivRecord.LABEL, rec_uuid))
                rels.append(relationship_factory(AUTHORED_BY, ArxivRecord.LABEL, rec_uuid, Author.LABEL, au_id))

            rels.append(relationship_factory(SUMMARIZES, Abstract.LABEL, ab_uuid, ArxivRecord.LABEL, rec_uuid))
            rels.append(relationship_factory(SUMMARIZED_BY, ArxivRecord.LABEL, rec_uuid, Abstract.LABEL, ab_uuid))

            for i, cat in enumerate(record.get("categories", "")):
                if i == 0:
                    rels.append(
                        relationship_factory(
                            PRIMARILY_CATEGORIZED_BY,
                            ArxivRecord.LABEL,
                            rec_uuid,
                            ArxivCategory.LABEL,
                            categories.get(cat).uuid,
                        )
                    )
                rels.append(
                    relationship_factory(
                        CATEGORIZES, ArxivCategory.LABEL, categories.get(cat).uuid, ArxivRecord.LABEL, rec_uuid
                    )
                )
                rels.append(
                    relationship_factory(
                        CATEGORIZED_BY, ArxivRecord.LABEL, rec_uuid, ArxivCategory.LABEL, categories.get(cat).uuid
                    )
                )
                relationships.extend(rels)
        except Exception as e:
            logger.error(
                "An error occurred",
                method=generate_csv_data.__name__,
                error=str(e),
                arxiv_identifier=record.get("identifier") if record else None,
            )
            raise e
    return arxiv_records, authors, abstracts, relationships, malformed_records


def arxiv_record_factory(record) -> str:
    return f"{record['identifier']},{record['title']},{record['date']},{str(uuid.uuid4())}\n"


def author_factory(record: dict) -> list:
    auths = list(f"{x.get('last_name')},{x.get('first_name')},{str(uuid.uuid4())}\n" for x in record.get("authors", []))
    return auths


def abstract_factory(record: dict, bucket: str, records_prefix: str) -> str:
    key = f"{records_prefix}/{record.get(IDENTIFIER)}/{ABSTRACT}.json"
    return f"{record.get(ABSTRACT_URL)},{bucket},{key},{str(uuid.uuid4())}\n"


def relationship_factory(label: str, start_label: str, start_uuid: str, end_label: str, end_uuid: str) -> str:
    return f"{label},{start_label},{start_uuid},{end_label},{end_uuid},{str(uuid.uuid4())}\n"
