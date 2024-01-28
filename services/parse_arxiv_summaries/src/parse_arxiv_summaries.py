# Description: Parse arXiv research summaries and send them to be persisted.

import json
import logging
import os
from collections import defaultdict

import boto3
import defusedxml.ElementTree as ET

logger = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.INFO)

INTERNAL_SERVER_ERROR = "Internal server error"
NO_REGION_SPECIFIED = "No region specified"

cs_categories_inverted = {
    "Artifical Intelligence": "AI",
    "Hardware Architecture": "AR",
    "Computational Complexity": "CC",
    "Computational Engineering, Finance, and Science": "CE",
    "Computational Geometry": "CG",
    "Computation and Language": "CL",
    "Cryptography and Security": "CR",
    "Computer Vision and Pattern Recognition": "CV",
    "Computers and Society": "CY",
    "Databases": "DB",
    "Distributed, Parallel, and Cluster Computing": "DC",
    "Digital Libraries": "DL",
    "Discrete Mathematics": "DM",
    "Data Structures and Algorithms": "DS",
    "Emerging Technologies": "ET",
    "Formal Languages and Automata Theory": "FL",
    "General Literature": "GL",
    "Graphics": "GR",
    "Computer Science and Game Theory": "GT",
    "Human-Computer Interaction": "HC",
    "Information Retrieval": "IR",
    "Information Theory": "IT",
    "Machine Learning": "LG",
    "Logic in Computer Science": "LO",
    "Multiagent Systems": "MA",
    "Multimedia": "MM",
    "Mathematical Software": "MS",
    "Numerical Analysis": "NA",
    "Neural and Evolutionary Computing": "NE",
    "Networking and Internet Architecture": "NI",
    "Other Computer Science": "OH",
    "Operating Systems": "OS",
    "Performance": "PF",
    "Programming Languages": "PL",
    "Robotics": "RO",
    "Symbolic Computation": "SC",
    "Sound": "SD",
    "Software Engineering": "SE",
    "Social and Information Networks": "SI",
    "Systems and Control": "SY",
}


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

        bucket_name = event.get("bucket_name")
        key = event.get("filename")
        logger.info(f"Bucket name: {bucket_name}")
        if not bucket_name:
            logger.error("No bucket name specified")
            return {"statusCode": 500, "body": "No bucket name specified"}

        if not key:
            logger.error("No key specified")
            return {"statusCode": 500, "body": "No key specified"}

        persist_lambda_name = os.environ.get("PERSIST_LAMBDA_FUNCTION_NAME")
        logger.info(f"Persist lambda function name: {persist_lambda_name}")
        if not persist_lambda_name:
            return {"statusCode": 500, "body": "No persist lambda function name specified"}

        xml_data = load_xml_from_s3(bucket_name, key)
        parsed_data = parse_xml(xml_data)
        upload_to_s3(key, bucket_name, parsed_data)
        call_persist_summaries(persist_lambda_name, bucket_name, parsed_data)
        logger.info("Finished parsing arXiv daily summaries")
        return {"statusCode": 200, "body": "Success"}

    except Exception as e:
        logger.error(e)
        return {"statusCode": 500, "body": INTERNAL_SERVER_ERROR}


def log_initial_info(event: dict) -> None:
    """
    Logs initial info.

    Args:
        event (dict): Event.
    """
    logger.info(f"Received event: {event}")
    logger.info("Starting to parse arXiv summaries")


def load_xml_from_s3(bucket_name: str, key: str):
    """
    Loads XML from S3.

    Args:
        bucket_name (str): Bucket name.
        key (str): Key.

    Returns:
        XML.
    """
    logger.info(f"Loading XML from S3 bucket {bucket_name}")
    if not bucket_name:
        raise ValueError("Must provide a bucket name")
    if not key:
        raise ValueError("Must provide a key")

    s3 = boto3.resource("s3")
    obj = s3.Object(bucket_name, key)
    body = obj.get()["Body"].read()
    return ET.fromstring(body)


def parse_xml(xml_data: ET) -> dict:
    """
    Parses arXiv XML into a list of dictionaries of research summaries.

    Args:
        xml_data (ET.Element): XML element.

    Returns:
        Dictionary of research summaries.
    """
    if not xml_data:
        raise ValueError("Must provide XML data")

    try:
        extracted_data_chunk = defaultdict(list)
        logger.info("Parsing XML")

        ns = {"oai": "http://www.openarchives.org/OAI/2.0/", "dc": "http://purl.org/dc/elements/1.1/"}
        records_found = 0
        records_with_valid_categories = 0
        for record in xml_data.findall(".//oai:record", ns):
            records_found += 1
            identifier = record.find(".//oai:identifier", ns).text
            abstract_url = record.find(".//dc:identifier", ns).text

            creators_elements = record.findall(".//dc:creator", ns)
            authors = []
            for creator in creators_elements:
                name_parts = creator.text.split(", ", 1)
                last_name = name_parts[0]
                first_name = name_parts[1] if len(name_parts) > 1 else ""
                authors.append({"last_name": last_name, "first_name": first_name})

            # Filter subjects based on cs_categories_inverted
            subjects_elements = record.findall(".//dc:subject", ns)
            categories = [
                cs_categories_inverted[subject.text]
                for subject in subjects_elements
                if subject.text in cs_categories_inverted
            ]
            if not categories:
                continue
            records_with_valid_categories += 1
            primary_category = categories[0]

            abstract = record.find(".//dc:description", ns).text
            title = record.find(".//dc:title", ns).text
            date = record.find(".//dc:date", ns).text
            group = "cs"

            extracted_data_chunk["records"].append(
                {
                    "identifier": identifier,
                    "abstract_url": abstract_url,
                    "authors": authors,
                    "primary_category": primary_category,
                    "categories": categories,
                    "abstract": abstract,
                    "title": title,
                    "date": date,
                    "group": group,
                }
            )
            if records_with_valid_categories == 1:
                logger.info(f"First record: {extracted_data_chunk['records'][0]}")
        logger.info(f"Found {records_found} records")
        logger.info(f"Found {records_with_valid_categories} records with valid CS categories")

    except ET.ParseError as e:
        logger.error(f"Parse error: {e}")
        raise e

    return extracted_data_chunk


def upload_to_s3(original_filename: str, bucket_name: str, xml: dict) -> None:
    """
    Uploads XML to S3.

    Args:
        original_filename (str): Original filename.
        bucket_name (str): Bucket name.
        xml (dict): XML.
    """
    logger.info("Uploading to S3 bucket " + bucket_name + " as " + original_filename + "_parsed.xml")
    s3 = boto3.client("s3")
    s3.put_object(
        Body=json.dumps(xml), Bucket=bucket_name, Key=(original_filename + "_parsed.json").replace("raw", "parsed")
    )


def call_persist_summaries(persist_lambda_name: str, bucket_name: str, filename: str) -> None:
    """
    Calls persist summaries.

    Args:
        persist_lambda_name (str): Persist lambda name.
        bucket_name (str): Bucket name.
        filename (str): Filename of the parsed summaries saved as xml.
    """
    logger.info(
        "Calling persist summaries function {persist_lambda_name} \
                 for {filename} in {bucket_name}"
    )
    event_payload = {"bucket_name": bucket_name, "filename": filename}
    lambda_client = boto3.client("lambda")
    lambda_client.invoke(FunctionName=persist_lambda_name, InvocationType="Event", Payload=event_payload)
