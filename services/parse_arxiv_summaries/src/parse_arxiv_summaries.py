# Description: Parse arXiv research summaries and send them to be persisted.

import json
import logging
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
        bucket_name = "dev-atomiklabs-data-bucket"
        key = "raw_data/data_ingestion/2024-03-08T21-53-02.json"
        print("loading xml data")
        xml_data = load_xml_from_s3(bucket_name, key)
        print(len(xml_data))
        print(xml_data[0])
        extracted_data = []
        for xml in xml_data:
            extracted_data.append(parse_xml_data(xml, "2024-03-05"))
        len(extracted_data)
        upload_to_s3(key, bucket_name, extracted_data)
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


def load_xml_from_s3(bucket_name: str, key: str) -> list[ET]:
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
    return json.loads(body)


def parse_xml_data(xml_data: str, from_date: str) -> dict:
    extracted_data_chunk = defaultdict(list)

    try:
        root = ET.fromstring(xml_data)
        ns = {"oai": "http://www.openarchives.org/OAI/2.0/", "dc": "http://purl.org/dc/elements/1.1/"}

        for record in root.findall(".//oai:record", ns):
            date_elements = record.findall(".//dc:date", ns)
            if len(date_elements) != 1:
                continue

            identifier = record.find(".//oai:identifier", ns).text
            abstract_url = record.find(".//dc:identifier", ns).text

            creators_elements = record.findall(".//dc:creator", ns)
            authors = []
            for creator in creators_elements:
                name_parts = creator.text.split(", ", 1)
                last_name = name_parts[0]
                first_name = name_parts[1] if len(name_parts) > 1 else ""
                authors.append({"last_name": last_name, "first_name": first_name})

            # Find all subjects
            subjects_elements = record.findall(".//dc:subject", ns)
            categories = [cs_categories_inverted.get(subject.text, "") for subject in subjects_elements]
            # Remove empty strings
            categories = list(filter(None, categories))
            primary_category = categories[0] if categories else ""

            abstract = record.find(".//dc:description", ns).text.replace("\n", " ")
            title = record.find(".//dc:title", ns).text.replace("\n", "")
            date = date_elements[0].text
            group = "cs"

            extracted_data_chunk["records"].append(
                {
                    "identifier": identifier,
                    "abstract_url": abstract_url,
                    "authors": authors,
                    "primary_category": primary_category,
                    "categories": categories,  # All categories
                    "abstract": abstract,
                    "title": title,
                    "date": date,
                    "group": group,
                }
            )

    except ET.ParseError as e:
        print(f"Parse error: {e}")

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


if __name__ == "__main__":
    lambda_handler({}, {})