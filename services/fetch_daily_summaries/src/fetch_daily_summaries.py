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

        required_env_vars = [aurora_cluster_arn, db_credentials_secret_arn, database, base_url, bucket_name, summary_set]
        if not all(required_env_vars):
            missing_vars = [var_name for var_name, var in zip(["RESOURCE_ARN", "SECRET_ARN", "DATABASE_NAME", "BASE_URL", "BUCKET_NAME", "SUMMARY_SET"], required_env_vars) if not var]
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
    return (datetime.today() - timedelta(days=1)).date()


def fetch_data_for_date(base_url: str, summary_set: str, fetch_date: date) -> str:
    params = {
        "verb": "ListRecords",
        "set": summary_set,
        "metadataPrefix": "oai_dc",
        "from": fetch_date.strftime("%Y-%m-%d"),
    }
    try:
        response = requests.get(base_url, params=params, timeout=60)
        if response.status_code == 200:
            return response.text
        else:
            logging.error(f"HTTP error for date {fetch_date}: {response.status_code}")
            return None
    except requests.RequestException as e:
        logging.error(f"Request exception for date {fetch_date}: {str(e)}")
        return None


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
        logging.error(f"Database query failed: {str(e)}")
        return False


def upload_to_s3(bucket_name: str, from_date: date, summary_set: str, xml_data: str):
    s3 = boto3.client("s3")
    file_key = f"arxiv/{summary_set}-{from_date.strftime('%Y-%m-%d')}.xml"
    try:
        s3.put_object(Body=xml_data, Bucket=bucket_name, Key=file_key)
        logging.info(f"Uploaded XML data for {from_date} to S3 bucket {bucket_name} with key {file_key}")
    except Exception as e:
        logging.error(f"Error uploading to S3: {str(e)}")


if __name__ == "__main__":
    lambda_handler({}, None)
