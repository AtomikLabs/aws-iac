import json
import os
import unittest
from unittest.mock import MagicMock, patch

from services.store_arxiv_summaries.src.store_arxiv_summaries.lambda_handler import (
    get_config,
    store_records,
    lambda_handler,
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
                "DATA_BUCKET": "test-bucket",
                "NEO4J_PASSWORD": "test-password",
                "NEO4J_URI": "test-uri",
                "NEO4J_USERNAME": "test-username",
                "SERVICE_NAME": "test-service",
                "SERVICE_VERSION": "test-version",
            },
        )

    def test_store_records_with_params_missing_or_wrong_type(self):
        records_param = [{"test": "test"}, {"test": "test"}]
        bucket_name_param = "test-bucket"
        key_param = "test-key"
        mock_config = {
            "DATA_BUCKET": "test-bucket",
            "NEO4J_PASSWORD": "test-password",
            "NEO4J_URI": "test-uri",
            "NEO4J_USERNAME": "test-username",
            "SERVICE_NAME": "test-service",
            "SERVICE_VERSION": "test-version",
        }
        with self.assertRaises(ValueError):
            store_records(None, bucket_name_param, key_param, mock_config)
        with self.assertRaises(ValueError):
            store_records(123, bucket_name_param, key_param, mock_config)
        with self.assertRaises(ValueError):
            store_records(records_param, None, key_param, mock_config)
        with self.assertRaises(ValueError):
            store_records(records_param, 123, key_param, mock_config)
        with self.assertRaises(ValueError):
            store_records(records_param, bucket_name_param, None, mock_config)

    @patch("services.store_arxiv_summaries.src.store_arxiv_summaries.lambda_handler.Neo4jDatabase")
    def test_store_records_with_valid_params(self, mock_neo4j_database):
        expected_results = {
            "stored": [{"test": "test"}, {"test": "test"}],
            "failed": [{"test": "test"}, {"test": "test"}],
        }
        records_param = [{"test": "test"}, {"test": "test"}]
        bucket_name_param = "test-bucket"
        key_param = "test-key"
        mock_neo4j_database().store_records.return_value = expected_results
        mock_config = {
            "DATA_BUCKET": "test-bucket",
            "NEO4J_PASSWORD": "test-password",
            "NEO4J_URI": "test-uri",
            "NEO4J_USERNAME": "test-username",
            "SERVICE_NAME": "test-service",
            "SERVICE_VERSION": "test-version",
        }
        result = store_records(records_param, bucket_name_param, key_param, mock_config)
        self.assertEqual(len(expected_results), len(result))

    @patch("services.store_arxiv_summaries.src.store_arxiv_summaries.lambda_handler.get_config")
    @patch("services.store_arxiv_summaries.src.store_arxiv_summaries.lambda_handler.store_records")
    @patch("services.store_arxiv_summaries.src.store_arxiv_summaries.lambda_handler.Neo4jDatabase")
    @patch("services.store_arxiv_summaries.src.store_arxiv_summaries.lambda_handler.StorageManager")
    def test_lambda_handler_with_valid_params(
        self, mock_storage_manager, mock_neo4j_database, mock_store_records, mock_get_config
    ):
        mock_storage_manager().load.return_value = json.dumps([{"test": "test"}, {"test": "test"}])

    @patch("services.store_arxiv_summaries.src.store_arxiv_summaries.lambda_handler.urllib.parse.unquote_plus")
    @patch("services.store_arxiv_summaries.src.store_arxiv_summaries.lambda_handler.json.loads")
    @patch("services.store_arxiv_summaries.src.store_arxiv_summaries.lambda_handler.get_config")
    @patch("services.store_arxiv_summaries.src.store_arxiv_summaries.lambda_handler.StorageManager")
    @patch("services.store_arxiv_summaries.src.store_arxiv_summaries.lambda_handler.store_records")
    @patch("services.store_arxiv_summaries.src.store_arxiv_summaries.lambda_handler.log_initial_info")
    @patch("services.store_arxiv_summaries.src.store_arxiv_summaries.lambda_handler.structlog")
    def test_lambda_handler_success(
        self,
        mock_structlog,
        mock_log_initial_info,
        mock_store_records,
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
        self, mock_log_initial_info, mock_storage_manager_cls, mock_get_config, mock_json_loads, mock_unquote_plus
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

    @patch("services.store_arxiv_summaries.src.store_arxiv_summaries.lambda_handler.Neo4jDatabase")
    def test_store_records_with_well_formed_records(self, mock_neo4j_database):
        records_param = [
            {
                "identifier": "1234",
                "title": "Test Title",
                "authors": ["Author 1", "Author 2"],
                "group": "test-group",
                "abstract": "Test abstract",
                "date": "2023-05-01",
                "abstract_url": "https://example.com/abstract",
            },
            {
                "identifier": "5678",
                "title": "Another Test Title",
                "authors": ["Author 3"],
                "group": "test-group",
                "abstract": "Another test abstract",
                "date": "2023-05-02",
                "abstract_url": "https://example.com/abstract2",
            },
        ]
        bucket_name_param = "test-bucket"
        key_param = "test-key"
        mock_config = {
            "DATA_BUCKET": "test-bucket",
            "NEO4J_PASSWORD": "test-password",
            "NEO4J_URI": "test-uri",
            "NEO4J_USERNAME": "test-username",
            "SERVICE_NAME": "test-service",
            "SERVICE_VERSION": "test-version",
        }
        result = store_records(records_param, bucket_name_param, key_param, mock_config)
        mock_neo4j_database.assert_called_once_with("test-uri", "test-username", "test-password")
        mock_neo4j_database().store_arxiv_records.assert_called_once_with(
            "test-key", records_param, "test-service", "test-version"
        )
        self.assertEqual(result, {"stored": records_param, "failed": []})

    @patch("services.store_arxiv_summaries.src.store_arxiv_summaries.lambda_handler.Neo4jDatabase")
    def test_store_records_with_malformed_records(self, mock_neo4j_database):
        records_param = [
            {
                "identifier": "1234",
                "title": "Test Title",
                "authors": ["Author 1", "Author 2"],
                "group": "test-group",
                "abstract": "Test abstract",
                "date": "2023-05-01",
                "abstract_url": "https://example.com/abstract",
            },
            {
                "identifier": "5678",
                "title": "Another Test Title",
                "group": "test-group",
                "abstract": "Another test abstract",
                "date": "2023-05-02",
                "abstract_url": "https://example.com/abstract2",
            },
        ]
        bucket_name_param = "test-bucket"
        key_param = "test-key"
        mock_config = {
            "DATA_BUCKET": "test-bucket",
            "NEO4J_PASSWORD": "test-password",
            "NEO4J_URI": "test-uri",
            "NEO4J_USERNAME": "test-username",
            "SERVICE_NAME": "test-service",
            "SERVICE_VERSION": "test-version",
        }
        result = store_records(records_param, bucket_name_param, key_param, mock_config)
        mock_neo4j_database.assert_called_once_with("test-uri", "test-username", "test-password")
        mock_neo4j_database().store_arxiv_records.assert_called_once_with(
            "test-key", [records_param[0]], "test-service", "test-version"
        )
        self.assertEqual(result, {"stored": [records_param[0]], "failed": [records_param[1]]})

    @patch("services.store_arxiv_summaries.src.store_arxiv_summaries.lambda_handler.Neo4jDatabase")
    def test_store_records_with_exception(self, mock_neo4j_database):
        records_param = [
            {
                "identifier": "1234",
                "title": "Test Title",
                "authors": ["Author 1", "Author 2"],
                "group": "test-group",
                "abstract": "Test abstract",
                "date": "2023-05-01",
                "abstract_url": "https://example.com/abstract",
            },
        ]
        bucket_name_param = "test-bucket"
        key_param = "test-key"
        mock_config = {
            "DATA_BUCKET": "test-bucket",
            "NEO4J_PASSWORD": "test-password",
            "NEO4J_URI": "test-uri",
            "NEO4J_USERNAME": "test-username",
            "SERVICE_NAME": "test-service",
            "SERVICE_VERSION": "test-version",
        }
        mock_neo4j_database.side_effect = Exception("Test exception")
        with self.assertRaises(Exception):
            store_records(records_param, bucket_name_param, key_param, mock_config)
        mock_neo4j_database.assert_called_once_with("test-uri", "test-username", "test-password")