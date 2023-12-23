import logging
import os
from datetime import datetime, timedelta, date
import boto3
import requests
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.INFO)


def lambda_handler(event: dict, context) -> dict:
    try:
        aurora_cluster_arn = os.environ.get("RESOURCE_ARN")
        base_url = os.environ.get("BASE_URL")
        bucket_name = os.environ.get("BUCKET_NAME")
        db_credentials_secret_arn = os.environ.get("SECRET_ARN")
        database = os.environ.get("DATABASE_NAME")
        summary_set = os.environ.get("SUMMARY_SET")

        required_env_vars = [
            aurora_cluster_arn,
            db_credentials_secret_arn,
            database,
            base_url,
            bucket_name,
            summary_set,
        ]
        if not all(required_env_vars):
            missing_vars = [
                var_name
                for var_name, var in zip(
                    ["RESOURCE_ARN", "SECRET_ARN", "DATABASE_NAME", "BASE_URL", "BUCKET_NAME", "SUMMARY_SET"],
                    required_env_vars,
                )
                if not var
            ]
            return {"statusCode": 500, "body": f"Missing environment variables: {', '.join(missing_vars)}"}

        insert_fetch_status(datetime.today().date(), aurora_cluster_arn, db_credentials_secret_arn, database)
        earliest_unfetched_date = get_earliest_unfetched_date(aurora_cluster_arn, db_credentials_secret_arn, database)

        if earliest_unfetched_date is None:
            return {"statusCode": 200, "body": "No new dates to fetch"}

        dates_to_fetch = generate_date_list(earliest_unfetched_date, datetime.today().date())
        for date in dates_to_fetch:
            xml_data = fetch_data_for_date(base_url, summary_set, date)
            if xml_data:
                upload_to_s3(bucket_name, date, summary_set, xml_data)
                set_fetch_status(date, "success", aurora_cluster_arn, db_credentials_secret_arn, database)
            else:
                set_fetch_status(date, "failure", aurora_cluster_arn, db_credentials_secret_arn, database)

        return {"statusCode": 200, "body": "Process completed successfully"}
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return {"statusCode": 500, "body": "Internal server error"}


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


def get_earliest_unfetched_date(aurora_cluster_arn, db_credentials_secret_arn, database, days=2) -> date:
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
    logging.info(f"Past dates: {past_dates}")
    logging.info(f"Today's date: {today}")

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
        logging.info(f"Unfetched dates: {unfetched_dates}")

        earliest_date = min(unfetched_dates) if unfetched_dates else None
    except Exception as e:
        logging.error(f"Database query failed: {str(e)}")
        earliest_date = None

    return earliest_date


def generate_date_list(start_date: date, end_date: date) -> list:
    return [(start_date + timedelta(days=i)) for i in range((end_date - start_date).days + 3)]


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


def get_earliest_unfetched_date(aurora_cluster_arn, db_credentials_secret_arn, database, days=2) -> date:
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
    logging.info(f"Past dates: {past_dates}")
    logging.info(f"Today's date: {today}")

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
    today: date,
    earliest_unfetched_date: date,
) -> date:
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
        today (date): Today's date.
        earliest_unfetched_date (date): Earliest unfetched date.

    Returns:
    date: The last date for which fetch was successful.
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


def fetch_data(base_url: str, from_date: date, summary_set: str) -> List[str]:
    """
    Fetches data from the API.

    Args:
        base_url (str): Base URL for the API.
        from_date (date): Summary date.
        summary_set (str): Summary set.

    Returns:
        List[str]: List of XML responses.
    """
    full_xml_responses = []
    params = {
        "verb": "ListRecords",
        "set": summary_set,
        "metadataPrefix": "oai_dc",
        "from": fetch_date.strftime("%Y-%m-%d"),
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

        if xml_content.strip():
            full_xml_responses.append(xml_content)

        logging.info(f"API Call Status Code: {status_code}")
        logging.info(f"API Response Content: {xml_content[:500]}...")

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
    from_date: date,
    summary_set: str,
    bucket_name: str,
    aurora_cluster_arn: str,
    db_credentials_secret_arn: str,
    database: str,
    fetched_data: List[str],
) -> bool:
    """
    Processes the fetched data and uploads to S3 using AWS RDSDataService.

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
    # Changed the regular expression pattern to check for the presence of at least one <dc:date> tag
    pattern = r"<dc:date>\s*" + re.escape(from_date.strftime("%Y-%m-%d")) + r"\s*</dc:date>"

    success = any(re.search(pattern, xml, re.DOTALL) for xml in fetched_data)

    if success:
        logging.info(f"Data found for date: {from_date}, proceeding with upload.")
        upload_to_s3(bucket_name, from_date, summary_set, fetched_data)
        set_fetch_status(from_date, "success", aurora_cluster_arn, db_credentials_secret_arn, database)
    else:
        logging.warning(f"No matching data found for date: {from_date}, marking as failure.")
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
        logging.error(f"Error uploading to S3: {str(e)}")


if __name__ == "__main__":
    lambda_handler({}, None)
