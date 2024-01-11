# Description: Lambda function to fetch daily summaries from arXiv.

import logging
import os
import re
import time
from datetime import timedelta, datetime, date
from typing import List
import json
import requests
import boto3
from collections import defaultdict
from html import unescape
from docx import Document
import docx.opc.constants
import defusedxml.ElementTree as ET
from botocore.exceptions import NoRegionError

logger = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.INFO)

INTERNAL_SERVER_ERROR = "Internal server error"
NO_REGION_SPECIFIED = "No region specified"
NO_UNFETCHED_DATES_FOUND = "No unfetched dates found"

TEST_BASE_URL = 'http://export.arxiv.org/oai2'
TEST = False


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

        aurora_cluster_arn = os.environ.get("RESOURCE_ARN")
        base_url = os.environ.get("BASE_URL")
        bucket_name = os.environ.get("BUCKET_NAME")
        db_credentials_secret_arn = os.environ.get("SECRET_ARN")
        database = os.environ.get("DATABASE_NAME")
        summary_set = os.environ.get("SUMMARY_SET")

        if not all([aurora_cluster_arn, db_credentials_secret_arn, database, base_url, bucket_name, summary_set]):
            message = ""
            if not aurora_cluster_arn:
                message += "RESOURCE_ARN "
            if not db_credentials_secret_arn:
                message += "SECRET_ARN "
            if not database:
                message += "DATABASE_NAME "
            if not base_url:
                message += "BASE_URL "
            if not bucket_name:
                message += "BUCKET_NAME "
            if not summary_set:
                message += "SUMMARY_SET "

            return {"statusCode": 500, "body": f"Missing environment variables: {message}"}

        try:
            insert_fetch_status(today, aurora_cluster_arn, db_credentials_secret_arn, database)
        except Exception as e:
            logger.error(f"Error inserting fetch status: {str(e)}")
            return {"statusCode": 500, "body": INTERNAL_SERVER_ERROR}

        try:
            earliest_unfetched_date = get_earliest_unfetched_date(
                aurora_cluster_arn, db_credentials_secret_arn, database
            )
        except Exception as e:
            logger.error(f"Error fetching earliest unfetched date: {str(e)}")
            return {"statusCode": 500, "body": INTERNAL_SERVER_ERROR}

        if not earliest_unfetched_date:
            message = NO_UNFETCHED_DATES_FOUND
            logger.info(message)
            return {"statusCode": 200, "body": message}

        if not earliest_unfetched_date:
            logger.info(NO_UNFETCHED_DATES_FOUND)
            return {"statusCode": 200, "body": NO_UNFETCHED_DATES_FOUND}

        logger.info(f"Earliest unfetched date: {earliest_unfetched_date}")
        
        fetch_data(base_url, earliest_unfetched_date, summary_set)

        return {"statusCode": 200, "body": message}
    except NoRegionError:
        logger.error(NO_REGION_SPECIFIED)
        return {"statusCode": 500, "body": NO_REGION_SPECIFIED}
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {"statusCode": 500, "body": INTERNAL_SERVER_ERROR}


def log_initial_info(event: dict) -> None:
    """
    Logs initial info.

    Args:
        event (dict): Event.
    """
    logger.info(f"Received event: {event}")
    logger.info("Starting to fetch arXiv daily summaries")


def calculate_from_date() -> date:
    """Calculates from date for fetching summaries.

    Returns:
        date: From date.
    """
    today = datetime.today()
    yesterday = today - timedelta(days=1)
    return yesterday.date()


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
    client = boto3.client("rds-data")
    formatted_date = date.strftime("%Y-%m-%d")

    sql_statement = """
    INSERT INTO research_fetch_status (fetch_date, status)
    VALUES (CAST(:date AS DATE), 'pending') ON CONFLICT (fetch_date) DO NOTHING
    """

    parameters = [{"name": "date", "value": {"stringValue": formatted_date}}]

    response = client.execute_statement(
        resourceArn=aurora_cluster_arn,
        secretArn=db_credentials_secret_arn,
        database=database,
        sql=sql_statement,
        parameters=parameters,
    )
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
    client = boto3.client("rds-data")
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
        response = client.execute_statement(
            resourceArn=aurora_cluster_arn,
            secretArn=db_credentials_secret_arn,
            database=database,
            sql=sql_statement,
            parameters=parameters,
        )

        fetched_dates = [
            datetime.strptime(result[0]["stringValue"], "%Y-%m-%d").date() for result in response["records"]
        ]
        unfetched_dates = list(set(past_dates) - set(fetched_dates))
        logger.info(f"Unfetched dates: {unfetched_dates}")

        earliest_date = min(unfetched_dates) if unfetched_dates else None
    except Exception as e:
        logger.error(f"Database query failed: {str(e)}")
        earliest_date = None

    return earliest_date


def fetch_data(base_url: str, from_date: date, summary_set: str) -> None:
    """
    Fetches data from arXiv.

    Args:
        base_url (str): Base URL.
        from_date (date): Summary date.
        summary_set (str): Summary set.
    """
    logger.info(f"Fetching data from {base_url} for date {from_date}")

    if TEST:
        fetch_data_test(base_url, from_date, summary_set)
    else:
        fetch_data_prod(base_url, from_date, summary_set)


def get_fetch_status(date: date, aurora_cluster_arn, db_credentials_secret_arn, database):
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
    client = boto3.client("rds-data")
    formatted_date = date.strftime("%Y-%m-%d")

    sql_statement = """
    SELECT status FROM research_fetch_status
    WHERE fetch_date = CAST(:date AS DATE)
    """

    parameters = [{"name": "date", "value": {"stringValue": formatted_date}}]

    response = client.execute_statement(
        resourceArn=aurora_cluster_arn,
        secretArn=db_credentials_secret_arn,
        database=database,
        sql=sql_statement,
        parameters=parameters,
    )
    logger.info(f"Fetch status response: {response} for date: {date}")
    if response["records"]:
        return response["records"][0][0]["stringValue"]
    else:
        return None


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
    return [(start_date + timedelta(days=i)) for i in range((delta.days) + 1)]


def schedule_for_later() -> None:
    """
    Schedules the Lambda function for later.
    """
    future_time = datetime.today() + timedelta(hours=5)

    cron_time = future_time.strftime("%M %H %d %m ? %Y")

    client = boto3.client("events")

    client.put_rule(Name="DynamicRule", ScheduleExpression=f"cron({cron_time})", State="ENABLED")

    lambda_arn = f"arn:aws:lambda:{os.environ['AWS_REGION']}:\
        {os.environ['AWS_ACCOUNT_ID']}:function:\
            {os.environ['AWS_LAMBDA_FUNCTION_NAME']}"

    client.put_targets(
        Rule="DynamicRule",
        Targets=[{"Id": "reschedule-{os.environ['AWS_LAMBDA_FUNCTION_NAME']}}", "Arn": lambda_arn}],
    )


def update_research_fetch_status(
    from_date: date,
    summary_set: str,
    bucket_name: str,
    aurora_cluster_arn: str,
    db_credentials_secret_arn: str,
    database: str,
    fetched_data: List[str],
) -> bool:
    """
    Checks if research was found for a given date and updates that
    date's research fetch status

    Args:
        from_date (date): Summary date.
        summary_set (str): Summary set.
        bucket_name (str): S3 bucket name.
        aurora_cluster_arn (str): The ARN of the Aurora Serverless DB cluster.
        db_credentials_secret_arn (str): The ARN of the secret containing
        credentials to access the DB.
        database (str): Database name.
        fetched_data (List[str]): List of XML responses.

    Returns:
        bool: True if fetch was successful, False otherwise.
    """
    pattern = r"<dc:description>.*?<dc:date>" + re.escape(from_date.strftime("%Y-%m-%d")) + r"</dc:date>"

    success = any(re.search(pattern, xml, re.DOTALL) for xml in fetched_data)

    if success:
        set_fetch_status(from_date, "success", aurora_cluster_arn, db_credentials_secret_arn, database)
    else:
        set_fetch_status(from_date, "failure", aurora_cluster_arn, db_credentials_secret_arn, database)

    return success


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
    client = boto3.client("rds-data")

    try:
        sql_statement = "UPDATE research_fetch_status SET status = :status \
            WHERE fetch_date = CAST(:date AS DATE)"

        parameters = [
            {"name": "date", "value": {"stringValue": date.strftime("%Y-%m-%d")}},
            {"name": "status", "value": {"stringValue": status}},
        ]

        client.execute_statement(
            resourceArn=aurora_cluster_arn,
            secretArn=db_credentials_secret_arn,
            database=database,
            sql=sql_statement,
            parameters=parameters,
        )
        return True
    except Exception as e:
        logger.error(f"Database query failed: {str(e)}")
        return False


cs_categories_inverted = {
    'Computer Science - Artifical Intelligence': 'AI',
    'Computer Science - Hardware Architecture': 'AR',
    'Computer Science - Computational Complexity': 'CC',
    'Computer Science - Computational Engineering, Finance, and Science': 'CE',
    'Computer Science - Computational Geometry': 'CG',
    'Computer Science - Computation and Language': 'CL',
    'Computer Science - Cryptography and Security': 'CR',
    'Computer Science - Computer Vision and Pattern Recognition': 'CV',
    'Computer Science - Computers and Society': 'CY',
    'Computer Science - Databases': 'DB',
    'Computer Science - Distributed, Parallel, and Cluster Computing': 'DC',
    'Computer Science - Digital Libraries': 'DL',
    'Computer Science - Discrete Mathematics': 'DM',
    'Computer Science - Data Structures and Algorithms': 'DS',
    'Computer Science - Emerging Technologies': 'ET',
    'Computer Science - Formal Languages and Automata Theory': 'FL',
    'Computer Science - General Literature': 'GL',
    'Computer Science - Graphics': 'GR',
    'Computer Science - Computer Science and Game Theory': 'GT',
    'Computer Science - Human-Computer Interaction': 'HC',
    'Computer Science - Information Retrieval': 'IR',
    'Computer Science - Information Theory': 'IT',
    'Computer Science - Machine Learning': 'LG',
    'Computer Science - Logic in Computer Science': 'LO',
    'Computer Science - Multiagent Systems': 'MA',
    'Computer Science - Multimedia': 'MM',
    'Computer Science - Mathematical Software': 'MS',
    'Computer Science - Numerical Analysis': 'NA',
    'Computer Science - Neural and Evolutionary Computing': 'NE',
    'Computer Science - Networking and Internet Architecture': 'NI',
    'Computer Science - Other Computer Science': 'OH',
    'Computer Science - Operating Systems': 'OS',
    'Computer Science - Performance': 'PF',
    'Computer Science - Programming Languages': 'PL',
    'Computer Science - Robotics': 'RO',
    'Computer Science - Symbolic Computation': 'SC',
    'Computer Science - Sound': 'SD',
    'Computer Science - Software Engineering': 'SE',
    'Computer Science - Social and Information Networks': 'SI',
    'Computer Science - Systems and Control': 'SY'
}


if __name__ == "__main__":
    test_fetch_and_process()