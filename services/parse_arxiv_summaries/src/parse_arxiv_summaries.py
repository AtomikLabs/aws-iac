# Description: Parse arXiv research summaries and send them to be persisted

import logging
from datetime import datetime
from collections import defaultdict

import boto3
import defusedxml.ElementTree as ET

logger = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.INFO)

INTERNAL_SERVER_ERROR = "Internal server error"
NO_REGION_SPECIFIED = "No region specified"

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

        bucket_name = event["Records"][0]["s3"]["bucket"]["name"]
        key = event["Records"][0]["s3"]["object"]["key"]

        xml_data = load_xml_from_s3(bucket_name, key)
        parsed_data = parse_xml(xml_data)
        upload_to_s3(key, bucket_name, parsed_data)
        call_persist_summaries(bucket_name, parsed_data)

        return {
            "statusCode": 200,
            "body": "Success"
        }

    except Exception as e:
        logger.error(e)
        return {
            "statusCode": 500,
            "body": INTERNAL_SERVER_ERROR
        }


def log_initial_info(event: dict) -> None:
    """
    Logs initial info.

    Args:
        event (dict): Event.
    """
    logging.info(f"Received event: {event}")
    logging.info("Starting to fetch arXiv daily summaries")


def load_xml_from_s3(bucket_name: str, key: str) -> ET.Element:
    """
    Loads XML from S3.

    Args:
        bucket_name (str): Bucket name.
        key (str): Key.

    Returns:
        XML element.
    """
    s3 = boto3.resource("s3")
    obj = s3.Object(bucket_name, key)
    body = obj.get()["Body"].read()
    return ET.fromstring(body)


def parse_xml(xml_data: ET.Element) -> dict:
    """
    Parses arXiv XML into a list of dictionaries of research summaries.

    Args:
        xml_data (ET.Element): XML element.

    Returns:
        Dictionary of research summaries.
    """
    extracted_data_chunk = defaultdict(list)

    try:
        root = ET.fromstring(xml_data)
        ns = {
            'oai': 'http://www.openarchives.org/OAI/2.0/',
            'dc': 'http://purl.org/dc/elements/1.1/'
        }

        for record in root.findall(".//oai:record", ns):
            identifier = record.find(".//oai:identifier", ns).text
            abstract_url = record.find(".//dc:identifier", ns).text

            creators_elements = record.findall(".//dc:creator", ns)
            authors = []
            for creator in creators_elements:
                name_parts = creator.text.split(", ", 1)
                last_name = name_parts[0]
                first_name = name_parts[1] if len(name_parts) > 1 else ""
                authors.append({'last_name': last_name, 'first_name': first_name})

            # Filter subjects based on cs_categories_inverted
            subjects_elements = record.findall(".//dc:subject", ns)
            categories = [cs_categories_inverted[subject.text] for subject in subjects_elements
                          if subject.text in cs_categories_inverted]
            if not categories:
                continue

            primary_category = categories[0]

            abstract = record.find(".//dc:description", ns).text
            title = record.find(".//dc:title", ns).text
            date = record.find(".//dc:date", ns).text
            group = 'cs'

            extracted_data_chunk['records'].append({
                'identifier': identifier,
                'abstract_url': abstract_url,
                'authors': authors,
                'primary_category': primary_category,
                'categories': categories,
                'abstract': abstract,
                'title': title,
                'date': date,
                'group': group
            })

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
    logging.info(f"Uploading to S3 bucket {bucket_name}")
    s3 = boto3.resource("s3")
    s3.Bucket(bucket_name).put_object(
        Key=f"arxiv/parsed_summaries/{original_filename}_parsed.xml",
        Body=xml
    )


def call_persist_summaries(bucket_name: str, xml: dict) -> None:
    """
    Calls persist summaries.

    Args:
        bucket_name (str): Bucket name.
        xml (dict): XML.
    """
    logging.info("Calling persist summaries")
    lambda_client = boto3.client("lambda")
    lambda_client.invoke(
        FunctionName="persist_summaries",
        InvocationType="Event",
        Payload=xml
    )
