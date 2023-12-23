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
        base_url = os.environ.get("BASE_URL")
        bucket_name = os.environ.get("BUCKET_NAME")
        summary_set = os.environ.get("SUMMARY_SET")
        required_env_vars = [base_url, bucket_name, summary_set]

        if not all(required_env_vars):
            missing_vars = [
                var_name
                for var_name, var in zip(["BASE_URL", "BUCKET_NAME", "SUMMARY_SET"], required_env_vars)
                if not var
            ]
            return {"statusCode": 500, "body": f"Missing environment variables: {', '.join(missing_vars)}"}

        dates_to_fetch = generate_date_list(calculate_from_date(), datetime.today().date())
        for date in dates_to_fetch:
            xml_data = fetch_data_for_date(base_url, summary_set, date)
            if xml_data:
                upload_to_s3(bucket_name, date, summary_set, xml_data)

        return {"statusCode": 200, "body": "Process completed successfully"}
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return {"statusCode": 500, "body": "Internal server error"}


def generate_date_list(start_date: date, end_date: date) -> list:
    return [(start_date + timedelta(days=i)) for i in range((end_date - start_date).days + 1)]


def calculate_from_date() -> date:
    return (datetime.today() - timedelta(days=3)).date()


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
