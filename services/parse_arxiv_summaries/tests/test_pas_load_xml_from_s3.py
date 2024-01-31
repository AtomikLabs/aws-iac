import unittest
from unittest.mock import Mock, patch

from botocore.exceptions import ClientError

from services.parse_arxiv_summaries.src.parse_arxiv_summaries import load_xml_from_s3


class TestLoadXMLFromS3(unittest.TestCase):
    def setUp(self):
        with open("services/parse_arxiv_summaries/tests/resources/20240131-072844.json", "r") as file:
            self.mock_json_content = file.read()
        self.bucket_name = "test-bucket"
        self.key = "test.xml"
        self.mock_xml_content = self.mock_json_content

    @patch("services.parse_arxiv_summaries.src.parse_arxiv_summaries.boto3.resource")
    def test_load_xml_from_s3_success(self, mock_boto3_resource):
        assert True