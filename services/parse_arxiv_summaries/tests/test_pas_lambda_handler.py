import json
import os
import unittest
from unittest.mock import MagicMock, patch

from services.parse_arxiv_summaries.src.parse_arxiv_summaries.lambda_handler import get_config, lambda_handler

S3_KEY_DATE_FORMAT = "%Y-%m-%dT%H-%M-%S"


class TestLambdaHandler(unittest.TestCase):
    def setUp(self):
        self.event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": "test-key"},
                    }
                }
            ]
        }
        self.context = MagicMock()

    @patch.dict(
        os.environ,
        {
            "APP_NAME": "test-app",
            "DATA_BUCKET": "test-bucket",
            "ENVIRONMENT": "test-env",
            "ETL_KEY_PREFIX": "test-prefix",
            "NEO4J_PASSWORD": "test-password",
            "NEO4J_URI": "test-uri",
            "NEO4J_USERNAME": "test-username",
            "SERVICE_NAME": "test-service",
            "SERVICE_VERSION": "test-version",
        },
    )
    def test_get_config(self):
        config = get_config()
        self.assertEqual(
            config,
            {
                "APP_NAME": "test-app",
                "DATA_BUCKET": "test-bucket",
                "ENVIRONMENT": "test-env",
                "ETL_KEY_PREFIX": "test-prefix",
                "NEO4J_PASSWORD": "test-password",
                "NEO4J_URI": "test-uri",
                "NEO4J_USERNAME": "test-username",
                "SERVICE_NAME": "test-service",
                "SERVICE_VERSION": "test-version",
            },
        )

    # TODO: Add tests for parse_xml_data

    @patch("services.parse_arxiv_summaries.src.parse_arxiv_summaries.lambda_handler.StorageManager")
    @patch("services.parse_arxiv_summaries.src.parse_arxiv_summaries.lambda_handler.Neo4jDatabase")
    @patch("services.parse_arxiv_summaries.src.parse_arxiv_summaries.lambda_handler.parse_xml_data")
    @patch("services.parse_arxiv_summaries.src.parse_arxiv_summaries.lambda_handler.get_config")
    @patch("services.parse_arxiv_summaries.src.parse_arxiv_summaries.lambda_handler.get_output_key")
    @patch.dict(
        os.environ,
        {
            "APP_NAME": "test-app",
            "DATA_BUCKET": "test-bucket",
            "ENVIRONMENT_NAME": "test-env",
            "ETL_KEY_PREFIX": "test-prefix",
            "NEO4J_PASSWORD": "test-password",
            "NEO4J_URI": "test-uri",
            "NEO4J_USERNAME": "test-username",
            "SERVICE_NAME": "test-service",
            "SERVICE_VERSION": "test-version",
        },
        clear=True,
    )
    def test_lambda_handler(
        self, mock_get_output_key, mock_get_config, mock_parse_xml_data, mock_neo4j_manager, mock_storage_manager
    ):
        mock_get_output_key.return_value = "test-output-key"
        mock_get_config.get("ETL_KEY_PREFIX").return_value = "test-prefix"
        mock_get_config.get("SERVICE_NAME").return_value = "test-service"
        mock_get_config.get("SERVICE_VERSION").return_value = "test-version"
        mock_parse_xml_data.return_value = [
            {
                "identifier": "test-identifier",
                "abstract_url": "test-url",
                "authors": [{"last_name": "Doe", "first_name": "John"}],
                "primary_category": "AI",
                "categories": ["AI"],
                "abstract": "Test abstract",
                "title": "Test Title",
                "date": "2023-04-01",
                "group": "cs",
            }
        ]
        mock_storage_manager().load.return_value = json.dumps(["<xml>test</xml>"])
        mock_storage_manager().get_storage_key_date.return_value = "2023-04-01T00-00-00"
        mock_neo4j_manager().create_arxiv_parsed_node.return_value = None

        response = lambda_handler(self.event, self.context)
        self.assertEqual(response, {"statusCode": 200, "body": "Success"})
        mock_storage_manager().upload_to_s3.assert_called_once()


if __name__ == "__main__":
    unittest.main()
