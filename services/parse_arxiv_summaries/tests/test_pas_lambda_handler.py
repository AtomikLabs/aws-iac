import datetime
import json
import os
import unittest
from unittest.mock import MagicMock, patch

from services.parse_arxiv_summaries.src.parse_arxiv_summaries.lambda_handler import (
    get_config,
    get_output_key,
    lambda_handler,
    log_initial_info,
)


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
                "SERVICE_NAME": "test-service",
                "SERVICE_VERSION": "test-version",
            },
        )

    def test_log_initial_info(self):
        log_initial_info(self.event)

    # TODO: Add tests for parse_xml_data

    @patch("services.parse_arxiv_summaries.src.parse_arxiv_summaries.lambda_handler.date")
    def test_get_output_key(self, mock_date):
        mock_date.today.return_value = datetime.date(2023, 4, 1)
        config = {"ETL_KEY_PREFIX": "test-prefix"}
        with patch.dict(os.environ, {"ETL_KEY_PREFIX": "test-prefix"}):
            output_key = get_output_key(config)
            assert output_key == f"test-prefix/{mock_date.today()}-parsed_arxiv_summaries.json"

    @patch("services.parse_arxiv_summaries.src.parse_arxiv_summaries.lambda_handler.StorageManager")
    @patch("services.parse_arxiv_summaries.src.parse_arxiv_summaries.lambda_handler.parse_xml_data")
    @patch("services.parse_arxiv_summaries.src.parse_arxiv_summaries.lambda_handler.get_config")
    @patch.dict(
        os.environ,
        {
            "APP_NAME": "test-app",
            "DATA_BUCKET": "test-bucket",
            "ENVIRONMENT_NAME": "test-env",
            "ETL_KEY_PREFIX": "test-prefix",
            "SERVICE_NAME": "test-service",
            "SERVICE_VERSION": "test-version",
        },
        clear=True,
    )
    def test_lambda_handler(self, mock_get_config, mock_parse_xml_data, mock_storage_manager):
        mock_get_config.return_value = {"ETL_KEY_PREFIX": "test-prefix"}
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

        response = lambda_handler(self.event, self.context)
        self.assertEqual(response, {"statusCode": 200, "body": "Success"})
        mock_storage_manager().persist.assert_called_once()


if __name__ == "__main__":
    unittest.main()