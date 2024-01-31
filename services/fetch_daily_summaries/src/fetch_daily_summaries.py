# Description: Lambda function to fetch daily summaries from arXiv.

import json
import logging
import os
import os
import time
from datetime import date, datetime, timedelta

from datetime import date, datetime, timedelta

import boto3
import defusedxml.ElementTree as ET
import requests

from database import Database

logger = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.INFO)

BACKOFF_TIMES = [30, 120]


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

        logger.info(f"Today's date: {today}")
        config = get_config()

        db = Database(config.get("aurora_cluster_arn"), config.get("db_credentials_secret_arn"), config.get("database"))

        insert_fetch_status(date.today(), db)

        earliest = get_earliest_unfetched_date(today, db)

        xml_data_list = fetch_data(config.get("base_url"), earliest, config.get("summary_set"))
        logger.info(f"Number of XML responses: {len(xml_data_list)}")

        key = f"arxiv_daily_summaries/{date.today()}.json"
        persist_to_s3(config.get("bucket_name"), key, json.dumps(xml_data_list))
        notify_parser(config.get("bucket_name"), key)

        return {"statusCode": 200, "body": json.dumps({"message": "Success"})}

    except Exception as e:
        logger.error(e)
        return {"statusCode": 500, "body": json.dumps({"message": "Internal Server Error"})}


def get_config() -> dict:
    """
    Gets the config from the environment variables.

    Returns:
        dict: The config.
    """
    try:
        config = {
            "arxiv_summary_lambda": os.environ["ARXIV_SUMMARY_LAMBDA"],
            "aurora_cluster_arn": os.environ["RESOURCE_ARN"],
            "base_url": os.environ["BASE_URL"],
            "bucket_name": os.environ["BUCKET_NAME"],
            "database": os.environ["DATABASE_NAME"],
            "db_credentials_secret_arn": os.environ["SECRET_ARN"],
            "summary_set": os.environ["SUMMARY_SET"],
        }
    except KeyError as e:
        logger.error(f"Missing environment variable: {str(e)}")
        raise e

    return config


def calculate_from_date() -> date:
    """Calculates from date for fetching summaries.

    Returns:
        date: From date.
    """
    return datetime.today().date()


def log_initial_info(event: dict) -> None:
    """
    Logs initial info.

    Args:
        event (dict): Event.
    """
    logger.info(f"Received event: {event}")
    logger.info("Starting to fetch arXiv daily summaries")


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
        raise ValueError("Date is required")

    if not db:
        raise ValueError("Database is required")

    formatted_date = date.strftime("%Y-%m-%d")

    sql_statement = """
    INSERT INTO research_fetch_status (fetch_date, status)
    VALUES (CAST(:date AS DATE), 'pending') ON CONFLICT (fetch_date) DO NOTHING
    """

    parameters = [{"name": "date", "value": {"stringValue": formatted_date}}]

    response = db.execute_sql(sql_statement, parameters)
    return response


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
        raise ValueError("Today's date is required")

    if type(days) is not int or days < 1 or days > 10:
        raise ValueError("Days must be an int between 1 and 10")

    past_dates = [(today - timedelta(days=i)) for i in range(1, days + 1)]
    logger.info(f"Past dates: {past_dates}")
    logger.info(f"Today's date: {today}")

    placeholders = [f":date{i}" for i in range(len(past_dates))]
    placeholder_string = ", ".join(placeholders)
    sql_statement = f"""
    SELECT fetch_date FROM research_fetch_status
    WHERE fetch_date = ANY(ARRAY[{placeholder_string}]::DATE[]) AND status = 'success'
    """

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
        logger.info(f"Unfetched dates: {unfetched_dates}")

        earliest_date = min(unfetched_dates) if unfetched_dates else None
    except Exception as e:
        logger.error(f"Database query failed: {str(e)}")
        earliest_date = None

    return earliest_date


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
        raise TypeError("Date must be a date object")

    if date > datetime.today().date():
        raise ValueError("Date must be today or earlier")

    formatted_date = date.strftime("%Y-%m-%d")

    sql_statement = """
    SELECT status FROM research_fetch_status
    WHERE fetch_date = CAST(:date AS DATE)
    """

    parameters = [{"name": "date", "value": {"stringValue": formatted_date}}]

    response = db.execute_sql(sql_statement, parameters)
    logger.info(f"Fetch status response: {response} for date: {date}")
    if "records" in response and response["records"]:
        return response["records"][0][0].get("stringValue", "status_not_found")
    else:
        return "status_not_found"


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
            logging.info(f"Fetching data with parameters: {params}")
            response = requests.get(base_url, params=params, timeout=60)
            response.raise_for_status()
            full_xml_responses.append(response.text)
            root = ET.fromstring(response.content)
            resumption_token_element = root.find(".//{http://www.openarchives.org/OAI/2.0/}resumptionToken")

            if resumption_token_element is not None and resumption_token_element.text:
                logging.info(f"Found resumptionToken: {resumption_token_element.text}")
                print(f"Found resumptionToken: {resumption_token_element.text}")
                time.sleep(5)
                params = {"verb": "ListRecords", "resumptionToken": resumption_token_element.text}
                retries += 1
            else:
                break

        except requests.exceptions.HTTPError as e:
            logging.error(f"HTTP error occurred: {e}")
            logging.error(f"Response content: {response.text}")
            print(e)

            if response.status_code == 503:
                backoff_time = response.headers.get("Retry-After", backoff_times.pop(0) if backoff_times else None)
                if backoff_time is None:
                    logging.error("Exhausted all backoff times, stopping retries.")
                    break
                logging.warning(f"Received 503 error, backing off for {backoff_time} seconds.")
                print(f"Received 503 error, backing off for {backoff_time} seconds.")
                time.sleep(int(backoff_time))
            else:
                break

        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            break

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
        raise ValueError("Date is required")

    if not status:
        raise ValueError("Status is required")

    if not db:
        raise ValueError("Database is required")
    try:
        sql_statement = "UPDATE research_fetch_status SET status = :status \
            WHERE fetch_date = CAST(:date AS DATE)"

        parameters = [
            {"name": "date", "value": {"stringValue": date.strftime("%Y-%m-%d")}},
            {"name": "status", "value": {"stringValue": status}},
        ]

        db.execute_sql(sql_statement, parameters)
        return True
    except Exception as e:
        logger.error(f"Database query failed: {str(e)}")
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
        raise ValueError("Bucket name is required")

    if not key:
        raise ValueError("Key is required")

    if not content:
        raise ValueError("Content is required")

    s3 = boto3.resource("s3")
    s3.Bucket(bucket_name).put_object(Key=key, Body=content)


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
        raise ValueError("Lambda ARN is required")
    if not bucket_name:
        raise ValueError("Bucket name is required")

    if not key:
        raise ValueError("Key is required")

    client = boto3.client("lambda")
    payload = {"bucket_name": bucket_name, "key": key}
    client.invoke(
        FunctionName=lambda_arn,
        InvocationType="Event",
        Payload=json.dumps(payload),
    )
