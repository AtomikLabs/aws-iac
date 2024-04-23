import os
import unittest
from unittest.mock import MagicMock, patch

from services.store_arxiv_summaries.src.store_arxiv_summaries.lambda_handler import get_config, lambda_handler


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
            "RECORDS_PREFIX": "research_records",
            "SERVICE_NAME": "test-service",
            "SERVICE_VERSION": "test-version",
        },
    )
    def test_get_config(self):
        config = get_config()
        self.assertEqual(
            config,
            {
                "DATA_BUCKET": "test-bucket",
                "RECORDS_PREFIX": "research_records",
                "SERVICE_NAME": "test-service",
                "SERVICE_VERSION": "test-version",
            },
        )

    @patch("services.store_arxiv_summaries.src.store_arxiv_summaries.lambda_handler.urllib.parse.unquote_plus")
    @patch("services.store_arxiv_summaries.src.store_arxiv_summaries.lambda_handler.json.loads")
    @patch("services.store_arxiv_summaries.src.store_arxiv_summaries.lambda_handler.get_config")
    @patch("services.store_arxiv_summaries.src.store_arxiv_summaries.lambda_handler.StorageManager")
    @patch("services.store_arxiv_summaries.src.store_arxiv_summaries.lambda_handler.store_records")
    @patch("services.store_arxiv_summaries.src.store_arxiv_summaries.lambda_handler.log_initial_info")
    @patch("services.store_arxiv_summaries.src.store_arxiv_summaries.lambda_handler.structlog")
    def test_lambda_handler_success(
        self,
        mock_log_initial_info,
        mock_storage_manager_cls,
        mock_get_config,
        mock_json_loads,
        mock_unquote_plus,
    ):
        mock_unquote_plus.return_value = "test-key.json"
        mock_get_config.return_value = {"key": "value"}
        mock_storage_manager = MagicMock()
        mock_storage_manager_cls.return_value = mock_storage_manager
        mock_json_loads.return_value = {"records": [{"id": 1}, {"id": 2}]}

        response = lambda_handler(self.event, self.context)

        mock_log_initial_info.assert_called_once_with(self.event)
        mock_unquote_plus.assert_called_once_with(self.event["Records"][0]["s3"]["object"]["key"], encoding="utf-8")
        mock_get_config.assert_called_once()
        self.assertEqual(response, {"statusCode": 200, "body": "Success"})

    @patch("services.store_arxiv_summaries.src.store_arxiv_summaries.lambda_handler.urllib.parse.unquote_plus")
    @patch("services.store_arxiv_summaries.src.store_arxiv_summaries.lambda_handler.json.loads")
    @patch("services.store_arxiv_summaries.src.store_arxiv_summaries.lambda_handler.get_config")
    @patch("services.store_arxiv_summaries.src.store_arxiv_summaries.lambda_handler.StorageManager")
    @patch("services.store_arxiv_summaries.src.store_arxiv_summaries.lambda_handler.log_initial_info")
    def test_lambda_handler_no_records(
        self, mock_storage_manager_cls, mock_get_config, mock_json_loads, mock_unquote_plus
    ):
        mock_unquote_plus.return_value = "test-key.json"
        mock_get_config.return_value = {}
        mock_storage_manager = MagicMock()
        mock_storage_manager_cls.return_value = mock_storage_manager
        mock_json_loads.return_value = {}
        response = lambda_handler(self.event, self.context)
        self.assertEqual(response, {"statusCode": 400, "body": "No records found"})

    @patch("services.store_arxiv_summaries.src.store_arxiv_summaries.lambda_handler.urllib.parse.unquote_plus")
    @patch("services.store_arxiv_summaries.src.store_arxiv_summaries.lambda_handler.log_initial_info")
    def test_lambda_handler_exception(self, mock_log_initial_info, mock_unquote_plus):
        mock_unquote_plus.side_effect = Exception("Test exception")

        response = lambda_handler(self.event, self.context)

        mock_log_initial_info.assert_called_once_with(self.event)
        mock_unquote_plus.assert_called_once_with(self.event["Records"][0]["s3"]["object"]["key"], encoding="utf-8")
        self.assertEqual(
            response,
            {"statusCode": 500, "body": "Internal server error", "error": "Test exception", "event": self.event},
        )
