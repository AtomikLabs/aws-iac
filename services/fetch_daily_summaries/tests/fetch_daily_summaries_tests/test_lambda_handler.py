import json
from datetime import date
from unittest.mock import MagicMock, patch

from services.fetch_daily_summaries.src.fetch_daily_summaries import lambda_handler


class TestLambdaHandler:
    @patch("services.fetch_daily_summaries.src.fetch_daily_summaries.log_initial_info")
    @patch("services.fetch_daily_summaries.src.fetch_daily_summaries.calculate_from_date")
    @patch("services.fetch_daily_summaries.src.fetch_daily_summaries.get_config")
    @patch("services.fetch_daily_summaries.src.fetch_daily_summaries.Database")
    @patch("services.fetch_daily_summaries.src.fetch_daily_summaries.insert_fetch_status")
    @patch("services.fetch_daily_summaries.src.fetch_daily_summaries.get_earliest_unfetched_date")
    @patch("services.fetch_daily_summaries.src.fetch_daily_summaries.fetch_data")
    @patch("services.fetch_daily_summaries.src.fetch_daily_summaries.persist_to_s3")
    @patch("services.fetch_daily_summaries.src.fetch_daily_summaries.notify_parser")
    @patch("services.fetch_daily_summaries.src.fetch_daily_summaries.logger")
    def test_lambda_handler_success(
        self,
        mock_logger,
        mock_notify_parser,
        mock_persist_to_s3,
        mock_fetch_data,
        mock_get_earliest_unfetched_date,
        mock_insert_fetch_status,
        mock_database,
        mock_get_config,
        mock_calculate_from_date,
        mock_log_initial_info,
    ):
        # Set up mock return values
        mock_calculate_from_date.return_value = date.today()
        mock_get_config.return_value = {
            "aurora_cluster_arn": "test_arn",
            "db_credentials_secret_arn": "test_secret_arn",
            "database": "test_db",
            "base_url": "http://testurl.com",
            "summary_set": "test_set",
            "bucket_name": "test_bucket",
        }
        mock_database.return_value = MagicMock()
        mock_get_earliest_unfetched_date.return_value = date.today()
        mock_fetch_data.return_value = [{"test": "data"}]
        mock_persist_to_s3.return_value = True

        # Call lambda_handler
        event = {}
        context = MagicMock()
        result = lambda_handler(event, context)

        # Asserts
        mock_log_initial_info.assert_called_once_with(event)
        mock_calculate_from_date.assert_called_once()
        mock_get_config.assert_called_once()
        mock_insert_fetch_status.assert_called_once()
        mock_get_earliest_unfetched_date.assert_called_once()
        mock_fetch_data.assert_called_once()
        mock_persist_to_s3.assert_called_once()
        mock_notify_parser.assert_called_once()

        assert result == {"statusCode": 200, "body": json.dumps({"message": "Success"})}

    @patch("services.fetch_daily_summaries.src.fetch_daily_summaries.log_initial_info")
    @patch("services.fetch_daily_summaries.src.fetch_daily_summaries.calculate_from_date")
    @patch("services.fetch_daily_summaries.src.fetch_daily_summaries.get_config")
    @patch("services.fetch_daily_summaries.src.fetch_daily_summaries.Database")
    @patch("services.fetch_daily_summaries.src.fetch_daily_summaries.insert_fetch_status")
    @patch("services.fetch_daily_summaries.src.fetch_daily_summaries.get_earliest_unfetched_date")
    @patch("services.fetch_daily_summaries.src.fetch_daily_summaries.fetch_data")
    @patch("services.fetch_daily_summaries.src.fetch_daily_summaries.persist_to_s3")
    @patch("services.fetch_daily_summaries.src.fetch_daily_summaries.notify_parser")
    @patch("services.fetch_daily_summaries.src.fetch_daily_summaries.logger")
    def test_lambda_handler_exception(
        self,
        mock_logger,
        mock_notify_parser,
        mock_persist_to_s3,
        mock_fetch_data,
        mock_get_earliest_unfetched_date,
        mock_insert_fetch_status,
        mock_database,
        mock_get_config,
        mock_calculate_from_date,
        mock_log_initial_info,
    ):
        # Set up mock to raise an exception
        mock_log_initial_info.side_effect = Exception("Test exception")

        # Call lambda_handler
        event = {}
        context = MagicMock()
        result = lambda_handler(event, context)

        # Asserts
        mock_logger.error.assert_called_once()
        assert result == {"statusCode": 500, "body": json.dumps({"message": "Internal Server Error"})}
