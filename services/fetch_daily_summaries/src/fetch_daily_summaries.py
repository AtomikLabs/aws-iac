# Description: Lambda function to fetch daily summaries from arXiv.

import requests
import json
import logging
import time
from html import unescape
import os
import os
import re
import boto3
import defusedxml.ElementTree as ET
from botocore.exceptions import NoRegionError
from datetime import datetime, timedelta, date
from typing import List
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.INFO)
TEST = False
AURORA_CLUSTER_ARN = ''
BASE_URL = ''
BUCKET_NAME = ''
DB_CREDENTIALS_SECRET_ARN = ''
DATABASE = ''
SUMMARY_SET = ''


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
        global AURORA_CLUSTER_ARN, BASE_URL, BUCKET_NAME, DB_CREDENTIALS_SECRET_ARN, DATABASE, SUMMARY_SET
        log_initial_info(event)

        today = calculate_from_date()

        logger.info(f"Today's date: {today}")
        AURORA_CLUSTER_ARN = os.environ.get('RESOURCE_ARN')
        BASE_URL = os.environ.get('BASE_URL')
        BUCKET_NAME = os.environ.get('BUCKET_NAME')
        DB_CREDENTIALS_SECRET_ARN = os.environ.get('SECRET_ARN')
        DATABASE = os.environ.get('DATABASE_NAME')
        SUMMARY_SET = os.environ.get('SUMMARY_SET')

        insert_fetch_status(date.today(), AURORA_CLUSTER_ARN, DB_CREDENTIALS_SECRET_ARN, DATABASE)
        earliest = get_earliest_unfetched_date(AURORA_CLUSTER_ARN, DB_CREDENTIALS_SECRET_ARN, DATABASE)
        xml_data_list = fetch_data(BASE_URL, earliest, SUMMARY_SET)
        logger.info(f"Number of XML responses: {len(xml_data_list)}")
        key = f"arxiv_daily_summaries/{date.today()}.json"
        persist_to_s3(BUCKET_NAME, key, json.dumps(xml_data_list))
        notify_parser(BUCKET_NAME, key)
    except Exception as e:
        logger.error(e)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Internal Server Error'
            })
        }


def get_config(test: bool = False) -> dict:
    """
    Gets the config from the environment variables.

    Returns:
        dict: The config.
    """
    try:
        if test:
            config = {
                "aurora_cluster_arn": "arn:aws:rds:us-east-1:758145997264:cluster:atomiklabs-dev-aurora-cluster",
                "base_url": "http://export.arxiv.org/oai2",
                "bucket_name": "atomiklabs-data-bucket-dev",
                "db_credentials_secret_arn": "arn:aws:secretsmanager:us-east-1:758145997264:secret:dev/database-credentials-TuF8OS",
                "database": "atomiklabs_dev_database",
                "summary_set": "cs",
            }
        else:
            config = {
                "aurora_cluster_arn": os.environ["RESOURCE_ARN"],
                "base_url": os.environ["BASE_URL"],
                "bucket_name": os.environ["BUCKET_NAME"],
                "db_credentials_secret_arn": os.environ["SECRET_ARN"],
                "database": os.environ["DATABASE_NAME"],
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
    today = datetime.today()
    yesterday = today - timedelta(days=0)
    return yesterday.date()


def log_initial_info(event: dict) -> None:
    """
    Logs initial info.

    Args:
        event (dict): Event.
    """
    logger.info(f"Received event: {event}")
    logger.info("Starting to fetch arXiv daily summaries")


def insert_fetch_status(date, aurora_cluster_arn, db_credentials_secret_arn, database):
    """
    Inserts fetch status as 'pending' for the given date using
    AWS RDSDataService.

    Args:
        date (date): Date for which to insert fetch status.
        aurora_cluster_arn (str): The ARN of the Aurora Serverless DB cluster.
        db_credentials_secret_arn (str): The ARN of the secret containing
                                         credentials to access the DB.
        database (str): Database name.
    """
    formatted_date = date.strftime("%Y-%m-%d")

    sql_statement = """
    INSERT INTO research_fetch_status (fetch_date, status)
    VALUES (CAST(:date AS DATE), 'pending') ON CONFLICT (fetch_date) DO NOTHING
    """

    parameters = [{"name": "date", "value": {"stringValue": formatted_date}}]

    response = execute_sql(sql_statement, parameters, aurora_cluster_arn, db_credentials_secret_arn, database)
    return response


def get_earliest_unfetched_date(aurora_cluster_arn, db_credentials_secret_arn, database, days=5) -> date:
    """
    Gets the earliest unfetched date using AWS RDSDataService.

    Args:
        aurora_cluster_arn (str): The ARN of the Aurora Serverless DB cluster.
        db_credentials_secret_arn (str): The ARN of the secret containing
                                         credentials to access the DB.
        database (str): Database name.
        days (int): Number of days to check for unfetched dates.

    Returns:
        date: Earliest unfetched date.
    """
    today = datetime.today().date()
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
        response = execute_sql(sql_statement, parameters, aurora_cluster_arn, db_credentials_secret_arn, database)

        fetched_dates = [
            datetime.strptime(result[0]["stringValue"], "%Y-%m-%d").date() for result in response["records"]
        ]
        unfetched_dates = list(set(past_dates) - set(fetched_dates))
        # prepend one day earlier than the earliest unfetched date (first date in the list)
        # arXiv doesn't always return the research for the date in the request (earliest date in this list)
        unfetched_dates.insert(0, unfetched_dates[0] - timedelta(days=1))
        logger.info(f"Unfetched dates: {unfetched_dates}")

        earliest_date = min(unfetched_dates) if unfetched_dates else None
    except Exception as e:
        logger.error(f"Database query failed: {str(e)}")
        earliest_date = None

    return earliest_date


def get_fetch_status(date: date, aurora_cluster_arn, db_credentials_secret_arn, database) -> str:
    """
    Gets fetch status for the given date using AWS RDSDataService.

    Args:
        date (date): Date for which to get fetch status.
        aurora_cluster_arn (str): The ARN of the Aurora Serverless DB cluster.
        db_credentials_secret_arn (str): The ARN of the secret containing
        credentials to access the DB.
        database (str): Database name.

    Returns:
        str: Fetch status.
    """
    formatted_date = date.strftime("%Y-%m-%d")

    sql_statement = """
    SELECT status FROM research_fetch_status
    WHERE fetch_date = CAST(:date AS DATE)
    """

    parameters = [{"name": "date", "value": {"stringValue": formatted_date}}]

    response = execute_sql(sql_statement, parameters, aurora_cluster_arn, db_credentials_secret_arn, database)
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
    """
    full_xml_responses = []
    params = {
        'verb': 'ListRecords',
        'set': set,
        'metadataPrefix': 'oai_dc',
        'from': from_date
    }

    backoff_times = [30, 120]

    while True:
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
                params = {'verb': 'ListRecords', 'resumptionToken': resumption_token_element.text}
            else:
                break

        except requests.exceptions.HTTPError as e:
            logging.error(f"HTTP error occurred: {e}")
            logging.error(f"Response content: {response.text}")
            print(e)

            if response.status_code == 503:
                backoff_time = response.headers.get('Retry-After', backoff_times.pop(0) if backoff_times else 30)
                logging.warning(f"Received 503 error, backing off for {backoff_time} seconds.")
                print(f"Received 503 error, backing off for {backoff_time} seconds.")
                time.sleep(int(backoff_time))
                continue

            break

        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            break

    return full_xml_responses


def execute_sql(sql_statement: str, parameters: List[dict], aurora_cluster_arn: str, db_credentials_secret_arn: str, database: str) -> dict:
    """
    Executes the given SQL statement using AWS RDSDataService.

    Args:
        sql_statement (str): SQL statement to execute.
        parameters (List[dict]): List of parameters.
        aurora_cluster_arn (str): The ARN of the Aurora Serverless DB cluster.
        db_credentials_secret_arn (str): The ARN of the secret containing
        credentials to access the DB.
        database (str): Database name.

    Returns:
        dict: Response from RDSDataService.
    """
    client = boto3.client("rds-data")

    try:
        response = client.execute_statement(
            resourceArn=aurora_cluster_arn,
            secretArn=db_credentials_secret_arn,
            database=database,
            sql=sql_statement,
            parameters=parameters,
        )
        return response
    except Exception as e:
        logger.error(f"Database query failed: {str(e)}")
        return {}


def generate_date_list(start_date: date, end_date: date) -> List[date]:
    """
    Generates a list of dates between the given start and end dates.

    Args:
        start_date (date): Start date.
        end_date (date): End date.

    Returns:
        List[date]: List of dates.
    """
    delta = end_date - start_date
    if delta.days < 0:
        raise ValueError("End date must be after start date")

    dates = []
    for i in range(delta.days + 1):
        research_date = start_date + timedelta(days=i)
        fetch_status = get_fetch_status(research_date, AURORA_CLUSTER_ARN, DB_CREDENTIALS_SECRET_ARN, DATABASE)
        if fetch_status != 'success':
            dates.append(research_date)
    return dates


def set_fetch_status(date: date, status, aurora_cluster_arn, db_credentials_secret_arn, database):
    """
    Sets fetch status in the database using AWS RDSDataService.

    Args:
        date (date): Date for which to set fetch status.
        status (str): Status to set ('success' or 'failure').
        aurora_cluster_arn (str): The ARN of the Aurora Serverless DB cluster.
        db_credentials_secret_arn (str): The ARN of the secret containing
        credentials to access the DB.
        database (str): Database name.
    """
    try:
        sql_statement = "UPDATE research_fetch_status SET status = :status \
            WHERE fetch_date = CAST(:date AS DATE)"

        parameters = [
            {"name": "date", "value": {"stringValue": date.strftime("%Y-%m-%d")}},
            {"name": "status", "value": {"stringValue": status}},
        ]

        execute_sql(sql_statement, parameters, aurora_cluster_arn, db_credentials_secret_arn, database)
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
    """
    s3 = boto3.resource("s3")
    s3.Bucket(bucket_name).put_object(Key=key, Body=content)


def notify_parser(bucket_name: str, key: str) -> None:
    """
    Notifies the parser Lambda function that new data is available.

    Args:
        bucket_name (str): Bucket name.
        key (str): Key.
    """
    client = boto3.client("lambda")
    payload = {"bucket_name": bucket_name, "key": key}
    client.invoke(
        FunctionName=os.environ.get("ARXIV_SUMMARY_LAMBDA"),
        InvocationType="Event",
        Payload=json.dumps(payload),
    )


def config_for_test():
    global AURORA_CLUSTER_ARN, BASE_URL, BUCKET_NAME, DB_CREDENTIALS_SECRET_ARN, DATABASE, SUMMARY_SET, OPENAI_KEY
    AURORA_CLUSTER_ARN = "arn:aws:rds:us-east-1:758145997264:cluster:atomiklabs-dev-aurora-cluster"
    BASE_URL = "http://export.arxiv.org/oai2"
    BUCKET_NAME = "atomiklabs-data-bucket-dev"
    DB_CREDENTIALS_SECRET_ARN = "arn:aws:secretsmanager:us-east-1:758145997264:secret:dev/database-credentials-TuF8OS"
    DATABASE = "atomiklabs_dev_database"
    SUMMARY_SET = "cs"
    load_dotenv()
    OPENAI_KEY = os.environ.get('OPENAI_KEY')


if __name__ == '__main__':
    config_for_test()
    log_initial_info({"test": "test"})
    insert_fetch_status(date.today(), AURORA_CLUSTER_ARN, DB_CREDENTIALS_SECRET_ARN, DATABASE)
    earliest = get_earliest_unfetched_date(AURORA_CLUSTER_ARN, DB_CREDENTIALS_SECRET_ARN, DATABASE)
    xml_data_list = fetch_data(BASE_URL, earliest, SUMMARY_SET)
    logger.info(f"Number of XML responses: {len(xml_data_list)}")
    key = f"arxiv_daily_summaries/{date.today()}.json"
    persist_to_s3(BUCKET_NAME, key, json.dumps(xml_data_list))
    notify_parser(BUCKET_NAME, key)
