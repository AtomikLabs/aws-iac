import unittest
from unittest.mock import patch, Mock
import boto3
from botocore.exceptions import ClientError
import xml.etree.ElementTree as ET
from services.parse_arxiv_summaries.src.parse_arxiv_summaries import load_xml_from_s3

class TestLoadXMLFromS3(unittest.TestCase):
    def setUp(self):
        self.bucket_name = "test-bucket"
        self.key = "test.xml"
        self.mock_xml_content = "<root><child>Test</child></root>"

    @patch('services.parse_arxiv_summaries.src.parse_arxiv_summaries.boto3.resource')
    def test_load_xml_from_s3_success(self, mock_boto3_resource):
        mock_s3_resource = mock_boto3_resource.return_value
        mock_object = mock_s3_resource.Object.return_value
        mock_object.get.return_value = {"Body": Mock(read=Mock(return_value=self.mock_xml_content))}
        
        result = load_xml_from_s3(self.bucket_name, self.key)
        self.assertIsInstance(result, ET.Element)

    def test_load_xml_from_s3_missing_bucket_name(self):
        with self.assertRaises(ValueError):
            load_xml_from_s3("", self.key)

    def test_load_xml_from_s3_missing_key(self):
        with self.assertRaises(ValueError):
            load_xml_from_s3(self.bucket_name, "")

    @patch('services.parse_arxiv_summaries.src.parse_arxiv_summaries.boto3.resource')
    def test_load_xml_from_s3_s3_exception(self, mock_boto3_resource):
        mock_s3_resource = mock_boto3_resource.return_value
        mock_object = mock_s3_resource.Object.return_value
        mock_object.get.side_effect = ClientError({'Error': {}}, "GetObject")
        
        with self.assertRaises(ClientError):
            load_xml_from_s3(self.bucket_name, self.key)
