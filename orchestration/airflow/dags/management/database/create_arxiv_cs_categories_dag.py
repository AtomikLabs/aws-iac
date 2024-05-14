import argparse
import json
import logging
from datetime import datetime

import boto3
import pytz
import structlog
from models.arxiv_category import ArxivCategory
from models.arxiv_set import ArxivSet
from neo4j import GraphDatabase

structlog.configure(
    [
        structlog.stdlib.filter_by_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.dict_tracebacks,
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()
logger.setLevel(logging.INFO)

CS_CATEGORIES_INVERTED = {
    "Computer Science - Artificial Intelligence": "AI",
    "Computer Science - Hardware Architecture": "AR",
    "Computer Science - Computational Complexity": "CC",
    "Computer Science - Computational Engineering, Finance, and Science": "CE",
    "Computer Science - Computational Geometry": "CG",
    "Computer Science - Computation and Language": "CL",
    "Computer Science - Cryptography and Security": "CR",
    "Computer Science - Computer Vision and Pattern Recognition": "CV",
    "Computer Science - Computers and Society": "CY",
    "Computer Science - Databases": "DB",
    "Computer Science - Distributed, Parallel, and Cluster Computing": "DC",
    "Computer Science - Digital Libraries": "DL",
    "Computer Science - Discrete Mathematics": "DM",
    "Computer Science - Data Structures and Algorithms": "DS",
    "Computer Science - Emerging Technologies": "ET",
    "Computer Science - Formal Languages and Automata Theory": "FL",
    "Computer Science - General Literature": "GL",
    "Computer Science - Graphics": "GR",
    "Computer Science - Computer Science and Game Theory": "GT",
    "Computer Science - Human-Computer Interaction": "HC",
    "Computer Science - Information Retrieval": "IR",
    "Computer Science - Information Theory": "IT",
    "Computer Science - Machine Learning": "LG",
    "Computer Science - Logic in Computer Science": "LO",
    "Computer Science - Multiagent Systems": "MA",
    "Computer Science - Multimedia": "MM",
    "Computer Science - Mathematical Software": "MS",
    "Computer Science - Numerical Analysis": "NA",
    "Computer Science - Neural and Evolutionary Computing": "NE",
    "Computer Science - Networking and Internet Architecture": "NI",
    "Computer Science - Other Computer Science": "OH",
    "Computer Science - Operating Systems": "OS",
    "Computer Science - Performance": "PF",
    "Computer Science - Programming Languages": "PL",
    "Computer Science - Robotics": "RO",
    "Computer Science - Symbolic Computation": "SC",
    "Computer Science - Sound": "SD",
    "Computer Science - Software Engineering": "SE",
    "Computer Science - Social and Information Networks": "SI",
    "Computer Science - Systems and Control": "SY",
    "NULL": "NULL",
}

DEFAULT_TIMEZONE = "US/Pacific"
S3_KEY_DATE_FORMAT = "%Y-%m-%dT%H-%M-%S"
DEFAULT_NEO4J_DB = "neo4j"
# get args from cli: -e <environment> -n <neo4j_uri>, env MUST be dev, prod, stage, or test
parser = argparse.ArgumentParser()
parser.add_argument("-e", "--env", help="Environment", required=True)
parser.add_argument("-n", "--neo4j_uri", help="Neo4j URI", required=True)
args = parser.parse_args()

env = args.env
if env not in ["dev", "prod", "stage", "test"]:
    raise ValueError("Invalid environment: must be dev, prod, stage, or test")

neo4j_uri = args.neo4j_uri


def get_storage_key_datetime(date: str = "") -> datetime:
    """
    Get the date in the format used for S3 keys.

    Args:
        date: The date to format.

    Returns:
        The date in the format used for S3 keys.
    """
    if not date:
        return datetime.now().astimezone(pytz.timezone(DEFAULT_TIMEZONE))
    return datetime.strptime(date, S3_KEY_DATE_FORMAT).astimezone(pytz.timezone(DEFAULT_TIMEZONE))


secret = boto3.client("secretsmanager").get_secret_value(SecretId=f"{env}/neo4j-credentials")
neo4j_creds = json.loads(secret["SecretString"])
print(neo4j_creds)

with GraphDatabase.driver(neo4j_uri, auth=(neo4j_creds["neo4j_username"], neo4j_creds["neo4j_password"])) as driver:
    with driver.session() as session:
        driver.verify_connectivity()
        logger.info("Connected to Neo4j")

        category_nodes = []
        now = get_storage_key_datetime().strftime(S3_KEY_DATE_FORMAT)
        arxiv_set = ArxivSet(driver, "CS", "Computer Science")
        arxiv_set.create()
        for name, code in CS_CATEGORIES_INVERTED.items():
            arxiv_category = ArxivCategory(driver, code, name)
            arxiv_category.create()
            arxiv_set.relate(
                driver, "CATEGORIZED_BY", ArxivSet.LABEL, arxiv_set.uuid, ArxivCategory.LABEL, arxiv_category.uuid
            )
            arxiv_category.relate(
                driver, "CATEGORIZES", ArxivCategory.LABEL, arxiv_category.uuid, ArxivSet.LABEL, arxiv_set.uuid
            )
    with driver.session() as session:
        driver.verify_connectivity()
        logger.info("Connected to Neo4j")
        session.run("CREATE INDEX arxiv_category_code IF NOT EXISTS FOR (n:ArxivCategory) ON (n.code);")
        session.run("CREATE INDEX arxiv_set_code IF NOT EXISTS FOR (n:ArxivSet) ON (n.code);")
        session.run("CREATE INDEX arxiv_record_uuid IF NOT EXISTS FOR (n:ArxivRecord) ON (n.uuid);")
        session.run("CREATE INDEX arxiv_record_identifier IF NOT EXISTS FOR (n:ArxivRecord) ON (n.identifier);")
        session.run("CREATE INDEX arxiv_record_date IF NOT EXISTS FOR (n:ArxivRecord) ON (n.date);")
        session.run("CREATE INDEX abstract_uuid IF NOT EXISTS FOR (n:Abstract) ON (n.uuid);")
        session.run("CREATE INDEX author_uuid IF NOT EXISTS FOR (n:Author) ON (n.uuid);")
        session.run("CREATE INDEX author_names IF NOT EXISTS FOR (n:Author) ON (n.first_name, n.last_name);")
