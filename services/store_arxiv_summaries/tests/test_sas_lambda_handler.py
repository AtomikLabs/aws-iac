import json
import os
import unittest
from unittest.mock import MagicMock, patch

from services.store_arxiv_summaries.src.store_arxiv_summaries.lambda_handler import (
    get_config,
    store_records,
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
        with self.assertRaises(ValueError):
            store_records(None, bucket_name_param, key_param)
        with self.assertRaises(ValueError):
            store_records(123, bucket_name_param, key_param)
        with self.assertRaises(ValueError):
            store_records(records_param, None, key_param)
        with self.assertRaises(ValueError):
            store_records(records_param, 123, key_param)
        with self.assertRaises(ValueError):
            store_records(records_param, bucket_name_param, None)

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
        result = store_records(records_param, bucket_name_param, key_param)
        self.assertEqual(len(expected_results), len(result))

    @patch("services.store_arxiv_summaries.src.store_arxiv_summaries.lambda_handler.get_config")
    @patch("services.store_arxiv_summaries.src.store_arxiv_summaries.lambda_handler.store_records")
    @patch("services.store_arxiv_summaries.src.store_arxiv_summaries.lambda_handler.Neo4jDatabase")
    @patch("services.store_arxiv_summaries.src.store_arxiv_summaries.lambda_handler.StorageManager")
    def test_lambda_handler_with_valid_params(
        self, mock_storage_manager, mock_neo4j_database, mock_store_records, mock_get_config
    ):
        mock_storage_manager().load.return_value = json.dumps([{"test": "test"}, {"test": "test"}])
