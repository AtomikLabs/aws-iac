# Description: Lambda function to fetch daily summaries from arXiv.

import logging
import os
import re
import time
from datetime import timedelta, datetime
from typing import List

import boto3
import defusedxml.ElementTree as ET
import requests
from botocore.exceptions import NoRegionError

logger = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.INFO)

INTERNAL_SERVER_ERROR = "Internal server error"
NO_REGION_SPECIFIED = "No region specified"
NO_UNFETCHED_DATES_FOUND = "No unfetched dates found"


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

        base_url, bucket_name, summary_set = get_event_params(event)

        today = calculate_from_date()

        aurora_cluster_arn = os.environ.get("RESOURCE_ARN")
        db_credentials_secret_arn = os.environ.get("SECRET_ARN")
        database = os.environ.get("DATABASE_NAME")

        if not all([aurora_cluster_arn, db_credentials_secret_arn, database]):
            return {"statusCode": 400, "body": "Configuration error: Missing required parameters"}

        try:
            insert_fetch_status(today, aurora_cluster_arn, db_credentials_secret_arn, database)
        except Exception as e:
            logging.error(f"Error inserting fetch status: {str(e)}")
            return {"statusCode": 500, "body": INTERNAL_SERVER_ERROR}

        try:
            earliest_unfetched_date = get_earliest_unfetched_date(
                aurora_cluster_arn, db_credentials_secret_arn, database
            )
        except Exception as e:
            logging.error(f"Error fetching earliest unfetched date: {str(e)}")
            return {"statusCode": 500, "body": INTERNAL_SERVER_ERROR}

        if not earliest_unfetched_date:
            message = NO_UNFETCHED_DATES_FOUND
            logging.info(message)
            return {"statusCode": 200, "body": message}

        if not earliest_unfetched_date:
            logging.info(NO_UNFETCHED_DATES_FOUND)
            return {"statusCode": 200, "body": NO_UNFETCHED_DATES_FOUND}

        logging.info(f"Earliest unfetched date: {earliest_unfetched_date}")

        try:
            last_success_date = attempt_fetch_for_dates(
                base_url,
                summary_set,
                bucket_name,
                aurora_cluster_arn,
                db_credentials_secret_arn,
                database,
                today,
                earliest_unfetched_date,
            )
        except Exception as e:
            logging.error(f"Error fetching summaries: {str(e)}")
            return {"statusCode": 500, "body": INTERNAL_SERVER_ERROR}

        if last_success_date:
            message = f"Last successful fetch date: {last_success_date}"
        else:
            message = "No new data fetched"

        return {"statusCode": 200, "body": message}
    except NoRegionError:
        logging.error(NO_REGION_SPECIFIED)
        return {"statusCode": 500, "body": NO_REGION_SPECIFIED}
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return {"statusCode": 500, "body": INTERNAL_SERVER_ERROR}


def log_initial_info(event: dict) -> None:
    """
    Logs initial info.

    Args:
        event (dict): Event.
    """
    logging.info(f"Received event: {event}")
    logging.info("Starting to fetch arXiv daily summaries")


def get_event_params(event: dict) -> (str, str, str):
    """
    Gets event parameters.

    Args:
        event (dict): Event.

    Returns:
        str: Base URL.
        str: S3 bucket name.
        str: Summary set.
    """
    if not event:
        return None, None, None

    return (event.get("base_url"), event.get("bucket_name"), event.get("summary_set"))


def calculate_from_date() -> str:
    """Calculates from date for fetching summaries.

    Returns:
        str: From date.
    """
    today = datetime.today()
    yesterday = today - timedelta(days=1)
    return yesterday.strftime("%Y-%m-%d")


def insert_fetch_status(date, aurora_cluster_arn, db_credentials_secret_arn, database):
    """
    Inserts fetch status as 'pending' for the given date using
    AWS RDSDataService.

    Args:
        date (str): Date for which to insert fetch status.
        aurora_cluster_arn (str): The ARN of the Aurora Serverless DB cluster.
        db_credentials_secret_arn (str): The ARN of the secret containing
                                         credentials to access the DB.
        database (str): Database name.
    """
    client = boto3.client("rds-data")

    sql_statement = """
    INSERT INTO research_fetch_status (fetch_date, status)
    VALUES (:date, 'pending') ON CONFLICT (fetch_date) DO NOTHING
    """

    parameters = [{"name": "date", "value": {"stringValue": date}}]

    response = client.execute_statement(
        resourceArn=aurora_cluster_arn,
        secretArn=db_credentials_secret_arn,
        database=database,
        sql=sql_statement,
        parameters=parameters,
    )
    return response


def get_earliest_unfetched_date(aurora_cluster_arn, db_credentials_secret_arn, database, days=5) -> datetime.date:
    client = boto3.client("rds-data")
    today = datetime.today().date()
    past_dates = [(today - timedelta(days=i)) for i in range(1, days + 1)]
    logging.info(f"Past dates: {past_dates}")
    logging.info(f"Today's date: {today}")
    sql_statement = """
    SELECT fetch_date FROM research_fetch_status
    WHERE fetch_date = ANY(ARRAY[{}]::DATE[]) AND status = 'success'
    """.format(', '.join(["%s::DATE"] * len(past_dates)))

    parameters = [{"name": "param" + str(i), "value": {"stringValue": date.strftime("%Y-%m-%d")}} for i, date in enumerate(past_dates)]

    try:
        response = client.execute_statement(
            resourceArn=aurora_cluster_arn,
            secretArn=db_credentials_secret_arn,
            database=database,
            sql=sql_statement,
            parameters=parameters,
        )

        fetched_dates = [datetime.strptime(result[0]["stringValue"], "%Y-%m-%d").date() for result in response["records"]]
        unfetched_dates = list(set(past_dates) - set(fetched_dates))
        logging.info(f"Unfetched dates: {unfetched_dates}")

        earliest_date = min(unfetched_dates) if unfetched_dates else None
    except Exception as e:
        logging.error(f"Database query failed: {str(e)}")
        earliest_date = None

    return earliest_date


def attempt_fetch_for_dates(
    base_url: str,
    summary_set: str,
    bucket_name: str,
    aurora_cluster_arn: str,
    db_credentials_secret_arn: str,
    database: str,
    today: str,
    earliest_unfetched_date: str,
):
    """
    Fetches arXiv daily summaries for the given dates using AWS RDSDataService.

    Args:
        base_url (str): Base URL for the API.
        summary_set (str): Summary set.
        bucket_name (str): S3 bucket name.
        aurora_cluster_arn (str): The ARN of the Aurora Serverless DB cluster.
        db_credentials_secret_arn (str): The ARN of the secret containing
        credentials to access the DB.
        database (str): Database name.
        today (str): Today's date.
        earliest_unfetched_date (str): Earliest unfetched date.

    Returns:
    str: The last date for which fetch was successful.
    """
    last_success_date = None

    if earliest_unfetched_date:
        full_xml_responses = fetch_data(base_url, earliest_unfetched_date, summary_set)
        date_list = generate_date_list(earliest_unfetched_date, today)
        logging.info(f"Date list: {date_list}")

        for date_to_fetch in date_list:
            logging.info(f"Fetching for date: {date_to_fetch}")
            insert_fetch_status(date_to_fetch, aurora_cluster_arn, db_credentials_secret_arn, database)
            success = process_fetch(
                date_to_fetch,
                summary_set,
                bucket_name,
                aurora_cluster_arn,
                db_credentials_secret_arn,
                database,
                full_xml_responses,
            )
            if success:
                logging.info(f"Fetch successful for date: {date_to_fetch}")
                last_success_date = date_to_fetch
            else:
                logging.error(f"Fetch failed for date: {date_to_fetch}")
    else:
        logging.warning(NO_UNFETCHED_DATES_FOUND)

    return last_success_date


def generate_date_list(start_date_str: str, end_date_str: str) -> List[str]:
    """
    Generates a list of dates between the given start and end dates.

    Args:
        start_date_str (str): Start date.
        end_date_str (str): End date.

    Returns:
        List[str]: List of dates.
    """
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    delta = end_date - start_date
    if delta.days < 0:
        raise ValueError("End date must be after start date")
    return [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range((delta.days) + 1)]


def fetch_data(base_url: str, from_date: str, summary_set: str) -> List[str]:
    """
    Fetches data from the API.

    Args:
        base_url (str): Base URL for the API.
        from_date (str): Summary date.
        summary_set (str): Summary set.

    Returns:
        List[str]: List of XML responses.
    """
    full_xml_responses = []
    params = {
        "verb": "ListRecords",
        "set": summary_set,
        "metadataPrefix": "oai_dc",
        "from": from_date,
    }
    retry_count = 0
    while True:
        if retry_count > 5:
            break
        status_code, xml_content = fetch_http_response(base_url, params)
        if status_code != 200:
            logging.error(f"HTTP error, probably told to back off: {status_code}")
            backoff_time = handle_http_error(status_code, xml_content, retry_count)
            if backoff_time:
                time.sleep(backoff_time)
                retry_count += 1
                continue
            else:
                break

        if xml_content.strip():  # Add this check
            full_xml_responses.append(xml_content)

        resumption_token = extract_resumption_token(xml_content)
        if resumption_token:
            logging.info(f"Resumption token: {resumption_token}")
            params = {"verb": "ListRecords", "resumptionToken": resumption_token}
            time.sleep(5)
        else:
            break

    return full_xml_responses


def fetch_http_response(base_url: str, params: dict) -> tuple[int, str]:
    """Fetches HTTP response.

    Args:
        base_url (str): Base URL for the API.
        params (dict): Request parameters.

    Returns:
        requests.Response: Response object.
    """
    response = requests.get(base_url, params=params, timeout=60)
    return response.status_code, response.text


def handle_http_error(status_code: int, response_text: str, retry_count: int) -> int:
    """
    Handles HTTP error.

    Args:
        status_code (int): HTTP status code.~
        response_text (str): Response text.
        retry_count (int): Retry count.

    Returns:
        int: Backoff time.
    """
    if "maintenance" in response_text.lower():
        schedule_for_later()
        return 0
    backoff_times = [30, 120]
    if status_code == 503 and retry_count < len(backoff_times):
        logging.info(
            f"Received 503, retrying after \
                {backoff_times[retry_count]} seconds"
        )
        return backoff_times[retry_count]
    return 0


def extract_resumption_token(xml_content: str) -> str:
    """Extracts resumption token from XML content.

    Args:
        xml_content (str): XML content.

    Returns:
        str: Resumption token.
    """
    try:
        root = ET.fromstring(xml_content)
        token_element = root.find(
            ".//{http://www.openarchives.org/OAI/2.0/}\
                                 resumptionToken"
        )
        return token_element.text if token_element is not None else None
    except ET.ParseError:
        return ""


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


def process_fetch(
    from_date, summary_set, bucket_name, aurora_cluster_arn, db_credentials_secret_arn, database, fetched_data
) -> bool:
    """
    Processes the fetched data and uploads to S3 using AWS RDSDataService.

    Args:
        from_date (str): Summary date.
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
    pattern = r"</dc:description>\s+<dc:date>" + re.escape(from_date)
    pattern += r"</dc:date>\s+<dc:type>text</dc:type>"
    success = any(re.search(pattern, xml) for xml in fetched_data)

    if success:
        upload_to_s3(bucket_name, from_date, summary_set, fetched_data)
        set_fetch_status(from_date, "success", aurora_cluster_arn, db_credentials_secret_arn, database)
    else:
        set_fetch_status(from_date, "failure", aurora_cluster_arn, db_credentials_secret_arn, database)

    return success


def set_fetch_status(date, status, aurora_cluster_arn, db_credentials_secret_arn, database):
    """
    Sets fetch status in the database using AWS RDSDataService.

    Args:
        date (str): Date for which to set fetch status.
        status (str): Status to set ('success' or 'failure').
        aurora_cluster_arn (str): The ARN of the Aurora Serverless DB cluster.
        db_credentials_secret_arn (str): The ARN of the secret containing
        credentials to access the DB.
        database (str): Database name.
    """
    client = boto3.client("rds-data")

    try:
        sql_statement = "UPDATE research_fetch_status SET status = :status \
            WHERE fetch_date = :date"

        parameters = [
            {"name": "date", "value": {"stringValue": date}},
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
        logging.error(f"Database query failed: {str(e)}")
        return False


def upload_to_s3(bucket_name: str, from_date: str, summary_set: str, full_xml_responses: List[str]):
    """Uploads XML responses to S3.

    Args:
        bucket_name (str): S3 bucket name.
        from_date (str): Summary date.
        summary_set (str): Summary set.
        full_xml_responses (List[str]): XML responses.
    """
    logging.info(f"Uploading {len(full_xml_responses)} XML responses to S3")
    s3 = boto3.client("s3")

    for idx, xml_response in enumerate(full_xml_responses):
        s3.put_object(
            Body=xml_response,
            Bucket=bucket_name,
            Key=f"arxiv/{summary_set}-{from_date}-{idx}.xml",
        )
