import json
from logging.config import dictConfig
from typing import Dict, List

import structlog
from dotenv import load_dotenv
from neo4j import Driver, GraphDatabase
from shared.database.s3_manager import S3Manager
from shared.models.abstract import Abstract
from shared.models.arxiv_category import ArxivCategory
from shared.models.arxiv_record import ArxivRecord
from shared.models.author import Author
from shared.models.data import Data
from shared.models.data_operation import DataOperation
from shared.utils.constants import (
    AIRFLOW_DAGS_ENV_PATH,
    AUTHORED_BY,
    AUTHORS,
    AWS_REGION,
    CATEGORIZED_BY,
    CATEGORIZES,
    CREATED_BY,
    CREATES,
    DATA_BUCKET,
    ENVIRONMENT_NAME,
    INTERMEDIATE_JSON_KEY,
    LOADED_BY,
    LOADS,
    LOGGING_CONFIG,
    NEO4J_PASSWORD,
    NEO4J_URI,
    NEO4J_USERNAME,
    ORCHESTRATION_HOST_PRIVATE_IP,
    PARSE_SUMMARIES_TASK,
    PERSIST_SUMMARIES_TASK,
    PERSIST_SUMMARIES_TASK_VERSION,
    PRIMARILY_CATEGORIZED_BY,
    RECORDS_PREFIX,
    SUMMARIZED_BY,
    SUMMARIZES,
)
from shared.utils.utils import get_config, get_storage_key_datetime

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
load_dotenv(dotenv_path=AIRFLOW_DAGS_ENV_PATH)

ABSTRACT = "abstract"
ABSTRACT_URL = "abstract_url"
CATEGORIES = "categories"
DATE = "date"
FIRST_NAME = "first_name"
IDENTIFIER = "identifier"
LAST_NAME = "last_name"
PRIMARY_CATEGORY = "primary_category"
TITLE = "title"


def run(**context: dict):
    try:
        logger.info("Running persist_summaries_task")
        env_vars = [
            AWS_REGION,
            DATA_BUCKET,
            ENVIRONMENT_NAME,
            ORCHESTRATION_HOST_PRIVATE_IP,
            PERSIST_SUMMARIES_TASK_VERSION,
            RECORDS_PREFIX,
        ]
        config = get_config(context, env_vars, neo4j=True)
        s3_manager = S3Manager(config.get(DATA_BUCKET), logger)
        key = context["ti"].xcom_pull(task_ids=PARSE_SUMMARIES_TASK, key=INTERMEDIATE_JSON_KEY)
        json_data = json.loads(s3_manager.load(key))
        if not json_data:
            logger.error("No records found", method=run.__name__, records_key=key, bucket_name=config.get(DATA_BUCKET))
            return {"statusCode": 400, "body": "No records found"}
        logger.info(
            "Storing parsed arXiv summary records)} records",
            method=run.__name__,
            num_records=len(json_data),
        )
        store_records(json_data, config.get(DATA_BUCKET), key, config, s3_manager)
        return {"statusCode": 200, "body": "Success"}
    except Exception as e:
        logger.error("An error occurred", method=run.__name__, error=str(e))
        return {"statusCode": 500, "body": "Internal server error", "error": str(e)}


def store_records(records: List[Dict], bucket_name: str, key: str, config: dict, storage_manager: S3Manager) -> Dict:
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
    try:
        filenames = []
        with GraphDatabase.driver(
            config.get(NEO4J_URI), auth=(config.get(NEO4J_USERNAME), config.get(NEO4J_PASSWORD))
        ) as driver:
            driver.verify_connectivity()
            parsed_data = parsed_data_node(driver, key)
            loads_dop = loads_dop_node(
                driver,
                "Load parsed arXiv records",
                PERSIST_SUMMARIES_TASK,
                config.get(PERSIST_SUMMARIES_TASK_VERSION),
                parsed_data,
            )
            categories = {c.code: c for c in ArxivCategory.find_all(driver)}
            possible_new_records = filter_new_records(driver, records)
            now = get_storage_key_datetime()
            props = {
                "created": now,
                "last_modified": now,
            }
            for record in possible_new_records:
                try:
                    arxiv_record = ArxivRecord(
                        driver=driver, arxiv_id=record.get(IDENTIFIER), title=record.get(TITLE), date=record.get(DATE)
                    )
                    arxiv_record.create()
                    arxiv_record.relate(
                        driver,
                        CREATED_BY,
                        DataOperation.LABEL,
                        loads_dop.uuid,
                        ArxivRecord.LABEL,
                        arxiv_record.uuid,
                        True,
                        props,
                    )
                    loads_dop.relate(
                        driver,
                        CREATES,
                        ArxivRecord.LABEL,
                        arxiv_record.uuid,
                        DataOperation.LABEL,
                        loads_dop.uuid,
                        True,
                        props,
                    )
                    record_categories = record.get(CATEGORIES) if record.get(CATEGORIES) else ["NULL"]
                    for i, category in enumerate(record_categories):
                        if i == 0:
                            arxiv_record.relate(
                                driver,
                                PRIMARILY_CATEGORIZED_BY,
                                arxiv_record.LABEL,
                                arxiv_record.uuid,
                                ArxivCategory.LABEL,
                                categories.get(category).uuid,
                                True,
                                props,
                            )
                        arxiv_record.relate(
                            driver,
                            CATEGORIZED_BY,
                            arxiv_record.LABEL,
                            arxiv_record.uuid,
                            ArxivCategory.LABEL,
                            categories.get(category).uuid,
                            True,
                            props,
                        )
                        categories.get(category).relate(
                            driver,
                            CATEGORIZES,
                            categories.get(category).LABEL,
                            categories.get(category).uuid,
                            arxiv_record.LABEL,
                            arxiv_record.uuid,
                            True,
                            props,
                        )
                except Exception as e:
                    logger.error("Failed to store arXiv record", error=str(e), method=store_records.__name__)
                    malformed_records.append(record)
                    continue
                try:
                    abstract_key = f"{config.get(RECORDS_PREFIX)}/{record.get(IDENTIFIER)}/{ABSTRACT}.json"
                    abstract = Abstract(
                        driver=driver,
                        abstract_url=record.get(ABSTRACT_URL),
                        bucket=config.get(DATA_BUCKET),
                        key=abstract_key,
                    )
                    abstract.create()
                    arxiv_record.relate(
                        driver,
                        SUMMARIZED_BY,
                        arxiv_record.LABEL,
                        arxiv_record.uuid,
                        abstract.LABEL,
                        abstract.uuid,
                        True,
                        props,
                    )
                    abstract.relate(
                        driver,
                        SUMMARIZES,
                        abstract.LABEL,
                        abstract.uuid,
                        arxiv_record.LABEL,
                        arxiv_record.uuid,
                        True,
                        props,
                    )
                    storage_manager.upload_to_s3(abstract_key, record.get(ABSTRACT))
                except Exception as e:
                    logger.error("Failed to store abstract", error=str(e), method=store_records.__name__)
                    malformed_records.append(record)
                try:
                    for author in record.get(AUTHORS, []):
                        author_node = Author(driver, author.get(FIRST_NAME), author.get(LAST_NAME))
                        author_node.create()
                        arxiv_record.relate(
                            driver,
                            AUTHORED_BY,
                            arxiv_record.LABEL,
                            arxiv_record.uuid,
                            Author.LABEL,
                            author_node.uuid,
                            True,
                            props,
                        )
                        author_node.relate(
                            driver,
                            AUTHORS,
                            Author.LABEL,
                            author_node.uuid,
                            arxiv_record.LABEL,
                            arxiv_record.uuid,
                            True,
                            props,
                        )
                except Exception as e:
                    logger.error("Failed to upload abstract to S3", error=str(e), method=store_records.__name__)
                    malformed_records.append(record)
    except Exception as e:
        logger.error(
            "An error occurred while committing arXiv records.",
            method=store_records.__name__,
            error=str(e),
        )
        raise e
    finally:
        logger.info("Malformed records", method=store_records.__name__, malformed_records=malformed_records)
        logger.info("Finished storing records", method=store_records.__name__)
        for filename in filenames:
            storage_manager.delete(filename)


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


def filter_new_records(driver: Driver, records: dict) -> list:
    """
    Filters out records that are already in the graph.

    Args:
        driver (Driver): The neo4j driver.
        records (dict): The records to filter.

    Returns:
        list: The identifiers of the new records.
    """
    params = {"identifiers": [record.get("identifier") for record in records]}
    result, _, _ = driver.execute_query(
        """
        UNWIND $identifiers AS identifier
        WITH identifier
        WHERE NOT EXISTS {
            MATCH (r:ArxivRecord {identifier: identifier})
        }
        RETURN identifier
        """,
        params,
        database="neo4j",
    )
    new_identifiers = [record["identifier"] for record in result]
    new_records = [record for record in records if record.get("identifier") in new_identifiers]
    return new_records
