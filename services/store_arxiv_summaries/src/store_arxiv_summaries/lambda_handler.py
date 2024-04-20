import json
import logging
import os
import urllib.parse
import uuid
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
            query = []
            query.append(f"""MATCH (n:{DataOperation.LABEL} {{uuid: "{loads_dop.uuid}"}})""")
            batch_size = 100
            total_records = len(records)
            num_batches = (total_records + batch_size - 1) // batch_size
            created_records = 0
            for batch_index in range(num_batches):
                start_index = batch_index * batch_size
                end_index = min((batch_index + 1) * batch_size, total_records)
                batch_records = records[start_index:end_index]
                for i, r in enumerate(batch_records):
                    query.append(
                        f"""MERGE (a{i}:ArxivRecord {{identifier: "{r.get(IDENTIFIER)}"}}) ON CREATE SET a{i}.title = "{r.get(TITLE)}", a{i}.date = "{r.get(DATE)}", a{i}.uuid = "{str(uuid.uuid4())}", a{i}.created = datetime({{timezone: 'America/Vancouver'}}), a{i}.last_modified = datetime({{timezone: 'America/Vancouver'}})"""
                    )
                    query.append(f"""MERGE (a{i})-[:{CREATED_BY}]->(n)""")
                    query.append(f"""MERGE (n)-[:{CREATES}]->(a{i})""")
                    for j, a in enumerate(r.get("authors", [])):
                        query.append(
                            f"""MERGE (au{i}_{j}:Author {{last_name: "{a.get("last_name")}", first_name: "{a.get("first_name")}"}}) ON CREATE SET au{i}_{j}.uuid = "{str(uuid.uuid4())}", au{i}_{j}.created = datetime({{timezone: 'America/Vancouver'}}), au{i}_{j}.last_modified = datetime({{timezone: 'America/Vancouver'}})"""
                        )
                        query.append(f"""MERGE (a{i})-[:{AUTHORED_BY}]->(au{i}_{j})""")
                        query.append(f"""MERGE (au{i}_{j})-[:{AUTHORS}]->(a{i})""")
                    query.append(
                        f"""MERGE (a{i}_abs:Abstract {{abstract_url: "{r.get(ABSTRACT_URL)}"}}) ON CREATE SET a{i}_abs.bucket = "{bucket_name}", a{i}_abs.key = "{config.get(RECORDS_PREFIX)}/{r.get(IDENTIFIER)}/{ABSTRACT}.json", a{i}_abs.uuid = "{str(uuid.uuid4())}", a{i}_abs.created = datetime({{timezone: 'America/Vancouver'}}), a{i}_abs.last_modified = datetime({{timezone: 'America/Vancouver'}})"""
                    )
                    query.append(f"""MERGE (a{i})-[:{SUMMARIZED_BY}]->(a{i}_abs)""")
                    query.append(f"""MERGE (a{i}_abs)-[:{SUMMARIZES}]->(a{i})""")
                    for k, c in enumerate(r.get("categories", [])):
                        query.append(f"""MERGE (a{i})-[:{CATEGORIZES}]->(c{i}_{k}:ArxivCategory {{code: "{c}"}})""")
                        query.append(f"""MERGE (c{i}_{k})-[:{CATEGORIZED_BY}]->(a{i})""")
                        if k == 0:
                            query.append(f"""MERGE (a{i})-[:{PRIMARILY_CATEGORIZED_BY}]->(c{i}_{k})""")
                _, summary, _ = driver.execute_query(
                    "".join(query),
                    database_="neo4j",
                )
                created_records += summary.counters.nodes_created
                logger.info(
                    "Arxiv records created",
                    method=store_records.__name__,
                    nodes_created=summary.counters.nodes_created,
                    batch_start_index=start_index,
                    batch_end_index=end_index,
                )
            logger.info(
                "Finished creating arXiv records",
                method=store_records.__name__,
                num_records=total_records,
                num_created_records=created_records,
            )
    except Exception as e:
        logger.error("An error occurred", method=store_records.__name__, error=str(e))
        raise e
    finally:
        logger.info(
            "Finished storing records",
            method=store_records.__name__,
            num_records=len(records),
            num_malformed_records=len(malformed_records),
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
