import json
import logging
import os
import urllib.parse
from typing import Dict, List

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
from models.data import Data
from models.data_operation import DataOperation
from neo4j import Driver, GraphDatabase
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
    required_fields = ["identifier", "title", "authors", "group", "abstract", "date", "abstract_url"]
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
            categories = {}
            null_node = null_category_node(driver)
            categories.update({"NULL": null_node})
            for record in records:
                if not all(record.get(field) for field in required_fields) or len(record.get("authors", [])) < 1:
                    malformed_records.append(record)
                    logger.error("Malformed record", method=store_records.__name__, record=record)
                else:
                    arxiv_record = arxiv_record_factory(
                        driver, record, loads_dop, categories, bucket_name, storage_manager, config
                    )
                    well_formed_records.append(arxiv_record)
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


def null_category_node(driver: Driver) -> ArxivCategory:
    """
    Creates a null category node in the graph.

    Args:
        driver (Driver): The neo4j driver.

    Returns:
        ArxivCategory: The null category node.
    """
    null_category = ArxivCategory.find(driver, "NULL")
    if not null_category:
        null_category = ArxivCategory(driver, "NULL", "NULL")
        null_category.create()
    if not null_category:
        message = "Failed to create NULL category"
        logger.error(message, method=lambda_handler.__name__)
        raise RuntimeError(message)
    return null_category


def arxiv_record_factory(
    driver: Driver,
    record: dict,
    loads_dop: DataOperation,
    categories: dict,
    bucket: str,
    storage_manager: StorageManager,
    config: dict,
) -> ArxivRecord:
    """
    Creates an arXiv record node and its related nodes in the graph.

    Args:
        driver (Driver): The neo4j driver.
        record (dict): The arXiv record.
        loads_dop (DataOperation): The data operation node.
        categories (dict): Memoized ArxivCategory nodes.
        bucket (str): The S3 bucket name for the parsed arXiv records.
        storage_manager (StorageManager): The storage manager.
        config (dict): The configuration for the service.

    Returns:
        ArxivRecord: The arXiv record node.
    """
    arxiv_record = record_node(driver, record)
    relate_record_dop(driver, arxiv_record, loads_dop)
    try:
        relate_categories(driver, arxiv_record, record, categories)
    except Exception as e:
        logger.error("Error while relating categories", method=lambda_handler.__name__, error=str(e))
    for author in record.get(AUTHORS.lower(), ""):
        try:
            relate_author(driver, arxiv_record, author)
        except Exception as e:
            logger.error("Error while relating author", method=lambda_handler.__name__, error=str(e))
    try:
        abstract = relate_abstract(driver, arxiv_record, record, bucket, config.get(RECORDS_PREFIX))
        storage_manager.upload_to_s3(abstract.key, record.get(ABSTRACT, ""))
    except Exception as e:
        logger.error(
            "Error while created, relating, or saving abstract",
            method=lambda_handler.__name__,
            identifier=record.get(IDENTIFIER),
            key=abstract.key if abstract else None,
            error=str(e),
        )
    return arxiv_record


def record_node(driver: Driver, record: dict) -> ArxivRecord:
    """
    Finds or creates an ArxivRecord in the graph.

    Args:
        driver (Driver): The neo4j driver.
        record (dict): The arXiv record.

    Returns:
        ArxivRecord: The ArxivRecord node.

    Raises:
        RuntimeError: If the ArxivRecord node cannot be created.
    """
    arxiv_record = ArxivRecord.find(driver, record.get(IDENTIFIER))
    if not arxiv_record:
        arxiv_record = ArxivRecord(driver, record.get(IDENTIFIER), record.get(TITLE), record.get(DATE))
        arxiv_record.create()
    if not arxiv_record:
        logger.error("Failed to create ArxivRecord", method=lambda_handler.__name__)
        raise RuntimeError("Failed to create ArxivRecord")
    return arxiv_record


def relate_record_dop(driver: Driver, record: ArxivRecord, dop: DataOperation) -> None:
    """
    Relates an arXiv record node to the data operation node that
    created it.

    Args:
        driver (Driver): The neo4j driver.
        record (ArxivRecord): The arXiv record node.
        dop (DataOperation): The data operation node.
    """
    record.relate(driver, CREATES, DataOperation.LABEL, dop.uuid, ArxivRecord.LABEL, record.uuid, True)
    dop.relate(driver, CREATED_BY, ArxivRecord.LABEL, record.uuid, DataOperation.LABEL, dop.uuid, True)


def relate_categories(driver: Driver, arxiv_record: ArxivRecord, record: dict, categories: dict) -> dict:
    """
    Relates an arXiv record node to its categories.

    Args:
        driver (Driver): The neo4j driver.
        arxiv_record (ArxivRecord): The arXiv record node.
        record (dict): The arXiv record data.
        categories (List): The list of arXiv categories already seen.

    Returns:
        List: The list of arXiv categories.
    """
    for i, category in enumerate(record.get("categories", [])):
        relate_category(driver, arxiv_record, category, categories, i == 0)
    return categories


def relate_category(
    driver: Driver, arxiv_record: ArxivRecord, category: str, categories: dict, primary: bool = False
) -> ArxivCategory:
    """
    Relates an arXiv record node to its categories.

    Args:
        driver (Driver): The neo4j driver.
        arxiv_record (ArxivRecord): The arXiv record node.
        category (str): The category of the arXiv record.
        categories (List): The list of arXiv categories.
        primary (bool): True if the category is the primary category.

    Returns:
        ArxivCategory: The category node.
    """
    arxiv_category = categories.get(category, None)
    if not arxiv_category:
        arxiv_category = ArxivCategory.find(driver, category)
    if not arxiv_category:
        logger.error("Failed to find ArxivCategory", method=relate_category.__name__, category=category)
        return None
    if primary:
        arxiv_record.relate(
            driver,
            PRIMARILY_CATEGORIZED_BY,
            ArxivRecord.LABEL,
            arxiv_record.uuid,
            ArxivCategory.LABEL,
            arxiv_category.uuid,
            True,
        )
    arxiv_record.relate(
        driver, CATEGORIZED_BY, ArxivRecord.LABEL, arxiv_record.uuid, ArxivCategory.LABEL, arxiv_category.uuid, True
    )
    arxiv_record.relate(
        driver, CATEGORIZES, ArxivCategory.LABEL, arxiv_category.uuid, ArxivRecord.LABEL, arxiv_record.uuid, True
    )
    return arxiv_category


def relate_abstract(driver: Driver, arxiv_record: ArxivRecord, record: dict, bucket: str, key_prefix: str) -> Abstract:
    """
    creates an abstract node and relates it to the arXiv record node.

    Args:
        driver (Driver): The neo4j driver.
        arxiv_record (ArxivRecord): The arXiv record node.
        record (dict): The arXiv record.
        bucket (str): The S3 bucket name for abstract_storage.
        key_prefix (str): The key prefix for the abstract.

    Returns:
        Abstract: The abstract node.
    """
    abstract = Abstract.find(driver, record.get(ABSTRACT_URL))
    if abstract:
        return abstract
    abstract_key = f"{key_prefix}/{record.get(IDENTIFIER)}/{ABSTRACT}.json"
    abstract = Abstract(driver, record.get(ABSTRACT_URL), bucket, abstract_key)
    abstract.create()
    if not abstract:
        logger.error("Failed to create Abstract", method=relate_abstract.__name__)
        raise RuntimeError("Failed to create Abstract")
    arxiv_record.relate(
        driver, SUMMARIZED_BY, ArxivRecord.LABEL, arxiv_record.uuid, Abstract.LABEL, abstract.uuid, True
    )
    abstract.relate(driver, SUMMARIZES, Abstract.LABEL, abstract.uuid, ArxivRecord.LABEL, arxiv_record.uuid, True)
    return abstract


def relate_author(driver: Driver, arxiv_record: ArxivRecord, author: dict) -> Author:
    """
    Relates an arXiv record node to an author node.

    Args:
        driver (Driver): The neo4j driver.
        arxiv_record (ArxivRecord): The arXiv record node.
        author (str): The author of the arXiv record.

    Returns:
        Author: The author node.

    Raises:
        RuntimeError: If the author node cannot be found or created.
    """
    author_node = Author.find(driver, author.get("last_name"), author.get("first_name"))
    if not author_node:
        author_node = Author(driver, author.get("last_name"), author.get("first_name"))
        author_node.create()
    if not author_node:
        logger.error("Failed to create Author", method=relate_author.__name__)
        raise RuntimeError("Failed to create Author")
    arxiv_record.relate(driver, AUTHORED_BY, ArxivRecord.LABEL, arxiv_record.uuid, Author.LABEL, author_node.uuid, True)
    author_node.relate(driver, AUTHORS, Author.LABEL, author_node.uuid, ArxivRecord.LABEL, arxiv_record.uuid, True)
    return author_node
