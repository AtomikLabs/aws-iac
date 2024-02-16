# Description: Lambda function to fetch daily summaries from arXiv.

import json
import logging
import os
import time
from datetime import date, datetime, timedelta
from typing import List

import boto3
import defusedxml.ElementTree as ET
import requests
import structlog

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
BACKOFF_TIMES = [30, 120]

# Environment variables
APP_NAME = "app_name"
BASE_URL_STR = "base_url"
ENVIRONMENT = "environment"
GLUE_DATABASE_NAME = "glue_database_name"
GLUE_TABLE_NAME = "glue_table_name"
S3_BUCKET_NAME = "s3_bucket_name"
SUMMARY_SET_STR = "summary_set"

# Logging constants
CALCULATE_FROM_DATE = "fetch_daily_summaries.calculate_from_date"
FETCH_DATA = "fetch_daily_summaries.fetch_data"
GET_CONFIG = "fetch_daily_summaries.get_config"
GET_EARLIEST_UNFETCHED_DATE = "fetch_daily_summaries.get_earliest_unfetched_date"
GET_FETCH_STATUS = "fetch_daily_summaries.get_fetch_status"
GET_METADATA_SCHEMA = "fetch_daily_summaries.get_metadata_schema"
INSERT_FETCH_STATUS = "fetch_daily_summaries.insert_fetch_status"
LAMBDA_HANDLER = "fetch_daily_summaries.lambda_handler"
LAMBDA_NAME = "fetch_daily_summaries"
LOG_INITIAL_INFO = "fetch_daily_summaries.log_initial_info"
NOTIFY_PARSER = "fetch_daily_summaries.notify_parser"
PERSIST_TO_S3 = "fetch_daily_summaries.persist_to_s3"
SET_FETCH_STATUS = "fetch_daily_summaries.set_fetch_status"


class Database:
    def __init__(self, aurora_cluster_arn, db_credentials_secret_arn, database_name):
        """
        Initialize a Database object.

        Args:
            aurora_cluster_arn (str): The ARN of the Aurora cluster.
            db_credentials_secret_arn (str): The ARN of the secret containing the database credentials.
            database_name (str): The name of the database.

        Returns:
            None

        Raises:
            ValueError: If aurora_cluster_arn is None or an empty string.
            ValueError: If db_credentials_secret_arn is None or an empty string.
            ValueError: If database_name is None or an empty string.
        """
        if not aurora_cluster_arn:
            raise ValueError("aurora_cluster_arn must be a non-empty string")
        if not db_credentials_secret_arn:
            raise ValueError("db_credentials_secret_arn must be a non-empty string")
        if not database_name:
            raise ValueError("database_name must be a non-empty string")
        self.aurora_cluster_arn = aurora_cluster_arn
        self.db_credentials_secret_arn = db_credentials_secret_arn
        self.database_name = database_name

    def execute_sql(self, sql_statement: str, parameters: List[dict]) -> dict:
        """
        Executes the given SQL statement using AWS RDSDataService.

        Args:
            sql_statement (str): SQL statement to execute.
            parameters (List[dict]): List of parameters.

        Returns:
            dict: Response from RDSDataService.

        Raises:
            ValueError: If SQL statement is not provided.
            ValueError: If parameters are not provided.
        """
        if not sql_statement:
            raise ValueError("SQL statement is required")

        if not parameters:
            raise ValueError("Parameters are required")

        if not isinstance(parameters, list):
            raise ValueError("Parameters must be a list")

        client = boto3.client("rds-data")

        try:
            response = client.execute_statement(
                resourceArn=self.aurora_cluster_arn,
                secretArn=self.db_credentials_secret_arn,
                database=self.database_name,
                sql=sql_statement,
                parameters=parameters,
            )
            return response
        except Exception as e:
            logger.error(f"Database query failed: {str(e)}")
            return {}


def lambda_handler(event: dict, context) -> dict:
    """
    The main entry point for the Lambda function.

    Args:
        event (dict): The event data.
        context: The context data.

    Returns:
        dict: A dict with the status code and body.
    """
    try:
        log_initial_info(event)

        today = calculate_from_date()

        config = get_config()

        db = Database(
            config.get("aurora_cluster_arn"), config.get(DB_CREDENTIALS_SECRET_ARN_STR), config.get(DATABASE_STR)
        )

        insert_fetch_status(date.today(), db)

        earliest = get_earliest_unfetched_date(today, db)

        xml_data_list = fetch_data(config.get(BASE_URL_STR), earliest, config.get(SUMMARY_SET_STR))

        key_date = time.strftime("%Y%m%d-%H%M%S")
        key = f"arxiv_daily_summaries/{key_date}.json"
        persist_to_s3(config.get(BUCKET_NAME_STR), key, json.dumps(xml_data_list))
        notify_parser(config.get(ARXIV_SUMMARY_LAMBDA_STR), config.get(BUCKET_NAME_STR), key)

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
            APP_NAME: os.environ["APP_NAME"],
            BASE_URL_STR: os.environ["BASE_URL"],
            ENVIRONMENT: os.environ["ENVIRONMENT"],
            GLUE_DATABASE_NAME: os.environ["GLUE_DATABASE_NAME"],
            GLUE_TABLE_NAME: os.environ["GLUE_TABLE_NAME"],
            S3_BUCKET_NAME: os.environ["S3_BUCKET_NAME"],
            SUMMARY_SET_STR: os.environ["SUMMARY_SET"],
        }
        safe_config = {k: config[k] for k in set(list(config.keys())) - set([DB_CREDENTIALS_SECRET_ARN_STR])}
        logger.debug("Config", method=GET_CONFIG, config=safe_config)
    except KeyError as e:
        logger.error("Missing environment variable", method=GET_CONFIG, error=str(e))
        raise e

    return config


def get_metadata_schema(config: dict) -> dict:
    """
    Gets the metadata schema for data ingestion from the AWS Glue Data Catalog.

    Args:
        config (dict): The config.

    Returns:
        dict: The metadata schema.
    """
    try:
        glue = boto3.client("glue")
        response = glue.get_table(DatabaseName=config[GLUE_DATABASE_NAME], Name=config[GLUE_TABLE_NAME])
        schema = response["Table"]["StorageDescriptor"]["Columns"]
        logger.debug("Metadata schema", method=GET_METADATA_SCHEMA, schema=schema)
    except Exception as e:
        logger.exception("Failed to get metadata schema", method=GET_METADATA_SCHEMA, error=str(e))
        raise e

    return schema

def calculate_from_date() -> date:
    """Calculates from date for fetching summaries.

    Returns:
        date: From date.
    """
    today = datetime.today().date()
    logger.info("Today's date", method=CALCULATE_FROM_DATE, date=today)
    return today


def insert_fetch_status(date: date, db: Database) -> None:
    """
    Inserts fetch status as 'pending' for the given date using
    AWS RDSDataService.

    Args:
        date (date): Date for which to insert fetch status.
        db (Database): Database object.

    Throws:
        ValueError: If date is not provided.
        ValueError: If database is not provided.
    """
    if not date:
        logger.error("Date is required", method=INSERT_FETCH_STATUS)
        raise ValueError("Date is required")

    if not db:
        logger.error("Database is required", method=INSERT_FETCH_STATUS)
        raise ValueError("Database is required")

    try:
        formatted_date = date.strftime("%Y-%m-%d")
        # Update spaces in tests if changed here
        sql_statement = """
    INSERT INTO research_fetch_status (fetch_date, status)
    VALUES (CAST(:date AS DATE), 'pending') ON CONFLICT (fetch_date) DO NOTHING
    """

        parameters = [{"name": "date", "value": {"stringValue": formatted_date}}]

        response = db.execute_sql(sql_statement, parameters)
        return response
    except Exception as e:
        logger.exception("Database query failed", method=INSERT_FETCH_STATUS, error=str(e))
        raise e


def get_earliest_unfetched_date(today: date, db: Database, days=5) -> date:
    """
    Gets the earliest unfetched date using AWS RDSDataService.

    Args:
        today (date): Today's date.
        db (Database): Database object.
        days (int): Number of days to check for unfetched dates.

    Returns:
        date: Earliest unfetched date.

    Raises:
        ValueError: If today's date is not provided.
        ValueError: If days is not an int between 1 and 10.
    """
    if not today:
        logger.error("Today's date is required", method=GET_EARLIEST_UNFETCHED_DATE)
        raise ValueError("Today's date is required")

    if type(days) is not int or days < 1 or days > 10:
        logger.error("Days must be an int between 1 and 10", method=GET_EARLIEST_UNFETCHED_DATE)
        raise ValueError("Days must be an int between 1 and 10")

    past_dates = [(today - timedelta(days=i)) for i in range(1, days + 1)]
    logger.debug("Dates", method=GET_EARLIEST_UNFETCHED_DATE, dates=past_dates, days=days, today=today)

    placeholders = [f":date{i}" for i in range(len(past_dates))]
    placeholder_string = ", ".join(placeholders)
    # Issues doing this with the RDSDataService client, so using string formatting. No user input.
    sql_statement = f"""
    SELECT fetch_date FROM research_fetch_status
    WHERE fetch_date = ANY(ARRAY[{placeholder_string}]::DATE[]) AND status = 'success'
    """  # nosec

    parameters = [
        {"name": f"date{i}", "value": {"stringValue": date.strftime("%Y-%m-%d")}} for i, date in enumerate(past_dates)
    ]

    try:
        response = db.execute_sql(sql_statement, parameters)

        fetched_dates = [
            datetime.strptime(result[0]["stringValue"], "%Y-%m-%d").date() for result in response["records"]
        ]
        unfetched_dates = sorted(list(set(past_dates) - set(fetched_dates)))
        # prepend one day earlier than the earliest unfetched date (first date in the list)
        # arXiv doesn't always return the research for the date in the request (earliest date in this list)

        unfetched_dates.insert(0, unfetched_dates[0] - timedelta(days=1))
        logger.info("Unfetched dates", method=GET_EARLIEST_UNFETCHED_DATE, unfetched_dates=unfetched_dates)

        earliest_date = min(unfetched_dates) if len(unfetched_dates) > 1 else None
        logger.info("Earliest unfetched date", method=GET_EARLIEST_UNFETCHED_DATE, earliest_date=earliest_date)
        return earliest_date
    except Exception as e:
        logger.exception("Database query failed", method=GET_EARLIEST_UNFETCHED_DATE, error=str(e))
        raise e


def get_fetch_status(date: date, db: Database) -> str:
    """
    Gets fetch status for the given date using AWS RDSDataService.

    Args:
        date (date): Date for which to get fetch status.
        db (Database): Database object.

    Returns:
        str: Fetch status.

    Raises:
        TypeError: If date is not a date object.
        ValueError: If date is after today.
    """
    if isinstance(date, datetime.date.__class__) or not date:
        logger.error("Date must be a date object", method=GET_FETCH_STATUS)
        raise TypeError("Date must be a date object")

    if date > datetime.today().date():
        logger.error("Date must be today or earlier", method=GET_FETCH_STATUS)
        raise ValueError("Date must be today or earlier")

    formatted_date = date.strftime("%Y-%m-%d")

    sql_statement = """
    SELECT status FROM research_fetch_status
    WHERE fetch_date = CAST(:date AS DATE)
    """

    parameters = [{"name": "date", "value": {"stringValue": formatted_date}}]

    try:
        response = db.execute_sql(sql_statement, parameters)
        logger.debug("Fetch status response", method=GET_FETCH_STATUS, response=response, date=date)
        if "records" in response and response["records"]:
            return response["records"][0][0].get("stringValue", "status_not_found")
        else:
            return "status_not_found"
    except Exception as e:
        logger.error(f"get_fetch_status - database query failed: {str(e)}")
        raise e


def fetch_data(base_url: str, from_date: str, set: str) -> list:
    """
    Fetches data from arXiv.

    Args:
        base_url (str): Base URL.
        from_date (str): From date.
        set (str): Set.

    Returns:
        list: List of XML responses.

    Raises:
        ValueError: If base URL is not provided.
        ValueError: If from date is not provided.
        ValueError: If set is not provided.
    """
    backoff_times = BACKOFF_TIMES.copy()
    full_xml_responses = []
    params = {"verb": "ListRecords", "set": set, "metadataPrefix": "oai_dc", "from": from_date}
    retries = 0
    while retries < len(BACKOFF_TIMES):
        try:
            logger.info(
                "Fetching data from arXiv",
                method=FETCH_DATA,
                base_url=base_url,
                params=params,
                retries=retries,
                backoff_times=backoff_times,
            )
            response = requests.get(base_url, params=params, timeout=60)
            response.raise_for_status()
            full_xml_responses.append(response.text)
            root = ET.fromstring(response.content)
            resumption_token_element = root.find(".//{http://www.openarchives.org/OAI/2.0/}resumptionToken")

            if resumption_token_element is not None and resumption_token_element.text:
                logger.debug(
                    "Resumption token found", method=FETCH_DATA, resumption_token=resumption_token_element.text
                )
                time.sleep(5)
                params = {"verb": "ListRecords", "resumptionToken": resumption_token_element.text}
                retries += 1
            else:
                break

        except requests.exceptions.HTTPError as e:
            logger.exception("Error occurred while fetching data from arXiv", method=FETCH_DATA, error=str(e))

            if response.status_code == 503:
                backoff_time = response.headers.get("Retry-After", backoff_times.pop(0) if backoff_times else None)
                if backoff_time is None:
                    logger.exception("Exhausted all backoff times", method=FETCH_DATA)
                    break
                logger.warning("Retrying after backoff time", method=FETCH_DATA, backoff_time=backoff_time)
                time.sleep(int(backoff_time))
            else:
                break

        except Exception as e:
            logging.exception("Error occurred while fetching data from arXiv", method=FETCH_DATA, error=str(e))
            break
    logger.info("Fetched data from arXiv", method=FETCH_DATA, full_xml_responses=full_xml_responses)
    return full_xml_responses


def set_fetch_status(date: date, status: str, db: Database) -> bool:
    """
    Sets fetch status in the database using AWS RDSDataService.

    Args:
        date (date): Date for which to set fetch status.
        status (str): Status to set ('success' or 'failure').
        db (Database): Database object.

    Returns:
        bool: True if successful, False otherwise.

    Raises:
        ValueError: If date is not provided.
        ValueError: If status is not provided.
        ValueError: If database is not provided.
        Exception: If database query fails.
    """
    if not date:
        logger.error("Date is required", method=SET_FETCH_STATUS)
        raise ValueError("Date is required")

    if not status:
        logger.error("Status is required", method=SET_FETCH_STATUS)
        raise ValueError("Status is required")

    if not db:
        logger.error("Database is required", method=SET_FETCH_STATUS)
        raise ValueError("Database is required")
    try:
        sql_statement = "UPDATE research_fetch_status SET status = :status \
            WHERE fetch_date = CAST(:date AS DATE)"

        parameters = [
            {"name": "date", "value": {"stringValue": date.strftime("%Y-%m-%d")}},
            {"name": "status", "value": {"stringValue": status}},
        ]

        db.execute_sql(sql_statement, parameters)
        logger.debug("Set fetch status", method=SET_FETCH_STATUS, date=date, status=status)
        return True
    except Exception as e:
        logger.exception("Database query failed", method=SET_FETCH_STATUS, error=str(e))
        return False


def persist_to_s3(bucket_name: str, key: str, content: str) -> None:
    """
    Persists the given content to S3.

    Args:
        bucket_name (str): Bucket name.
        key (str): Key.
        content (str): Content.

    Raises:
        ValueError: If bucket name is not provided.
        ValueError: If key is not provided.
        ValueError: If content is not provided.
    """
    if not bucket_name:
        logger.error("Bucket name is required", method=PERSIST_TO_S3)
        raise ValueError("Bucket name is required")

    if not key:
        logger.error("Key is required", method=PERSIST_TO_S3)
        raise ValueError("Key is required")

    if not content:
        logger.error("Content is required", method=PERSIST_TO_S3)
        raise ValueError("Content is required")

    try:
        s3 = boto3.resource("s3")
        s3.Bucket(bucket_name).put_object(Key=key, Body=content)
        logger.info("Persisting content to S3", method=PERSIST_TO_S3, bucket_name=bucket_name, key=key)
    except Exception as e:
        logger.exception(
            "Failed to persist content to S3", method=PERSIST_TO_S3, bucket_name=bucket_name, key=key, error=str(e)
        )
        raise e


def notify_parser(lambda_arn: str, bucket_name: str, key: str) -> None:
    """
    Notifies the parser Lambda function that new data is available.

    Args:
        lambda_arn (str): Lambda ARN.
        bucket_name (str): Bucket name.
        key (str): Key.

    Raises:
        ValueError: If lambda ARN is not provided.
        ValueError: If bucket name is not provided.
        ValueError: If key is not provided.
    """
    if not lambda_arn:
        logger.error("Lambda ARN is required", method=NOTIFY_PARSER)
        raise ValueError("Lambda ARN is required")
    if not bucket_name:
        logger.error("Bucket name is required", method=NOTIFY_PARSER)
        raise ValueError("Bucket name is required")

    if not key:
        logger.error("Key is required", method=NOTIFY_PARSER)
        raise ValueError("Key is required")
    try:
        client = boto3.client("lambda")
        payload = {BUCKET_NAME_STR: bucket_name, "key": key}
        client.invoke(
            FunctionName=lambda_arn,
            InvocationType="Event",
            Payload=json.dumps(payload),
        )
        logger.debug(
            "Notified parser Lambda function",
            method=NOTIFY_PARSER,
            lambda_arn=lambda_arn,
            bucket_name=bucket_name,
            key=key,
        )
    except Exception as e:
        logger.exception(
            "Failed to notify parser Lambda function",
            method=NOTIFY_PARSER,
            lambda_arn=lambda_arn,
            bucket_name=bucket_name,
            key=key,
            error=str(e),
        )
        raise e
