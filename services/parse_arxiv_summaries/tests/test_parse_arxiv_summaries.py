# Test parsing of arXiv summaries

import unittest

from unittest.mock import patch, MagicMock, Mock
from services.parse_arxiv_summaries.src.parse_arxiv_summaries import (
    lambda_handler,
    log_initial_info,
    load_xml_from_s3,
    parse_xml,
    persist_summaries,
)
from xml.etree import ElementTree as ET

BASE_PATH = "services.parse_arxiv_summaries.src.parse_arxiv_summaries."
LAMBDA_HANDLER_PATH = BASE_PATH + "lambda_handler"
LOG_INITIAL_INFO_PATH = BASE_PATH + "log_initial_info"
LOAD_XML_FROM_S3_PATH = BASE_PATH + "load_xml_from_s3"
PARSE_XML_PATH = BASE_PATH + "parse_xml"
PERSIST_SUMMARIES_PATH = BASE_PATH + "persist_summaries"


class TestLambdaHandler(unittest.TestCase):
    pass


class TestLogInitialInfo(unittest.TestCase):
    pass


class TestLoadXmlFromS3(unittest.TestCase):
    pass


class TestParseXml(unittest.TestCase):
    pass


class TestPersistSummaries(unittest.TestCase):
    pass
