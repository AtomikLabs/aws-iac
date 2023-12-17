# Tests for database_operations.py
import logging
import unittest
from unittest.mock import patch, Mock
from datetime import datetime, timedelta
from services.fetch_daily_summaries.src.fetch_daily_summaries import (
    insert_fetch_status,
    get_earliest_unfetched_date,
    set_fetch_status,
)


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

BASE_PATH = "services.fetch_daily_summaries.src.fetch_daily_summaries."
BOTO3_CLIENT_PATH = "boto3.client"
DATETIME_PATH = "fetch_daily_summaries.datetime.datetime.today"
DATABASE_ERROR = "Database error"


class TestInsertFetchStatus(unittest.TestCase):
    @patch(BASE_PATH + BOTO3_CLIENT_PATH)
    def test_successful_insert(self, mock_boto3_client):
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client
        mock_client.execute_statement.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}

        response = insert_fetch_status("2023-01-01", "mock_aurora_arn", "mock_secret_arn", "mock_database")

        mock_boto3_client.assert_called_once_with("rds-data")
        mock_client.execute_statement.assert_called_once()
        self.assertEqual(response, {"ResponseMetadata": {"HTTPStatusCode": 200}})

    @patch(BOTO3_CLIENT_PATH)
    def test_exception_on_insert(self, mock_boto3_client):
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client
        mock_client.execute_statement.side_effect = Exception(DATABASE_ERROR)

        with self.assertRaises(Exception) as context:
            insert_fetch_status("2023-01-01", "mock_aurora_arn", "mock_secret_arn", "mock_database")

        self.assertEqual(str(context.exception), DATABASE_ERROR)


class TestGetEarliestUnfetchedDate(unittest.TestCase):
    # Using the real today() is not best practice, but mocking was a pain
    # and not worth the effort for this simple test.
    BOTO3_CLIENT_PATH = BASE_PATH + "boto3.client"

    @patch(BOTO3_CLIENT_PATH)
    def test_successful_retrieval(self, mock_boto3_client):
        today = datetime.today().date()
        past_dates = [today - timedelta(days=i) for i in range(1, 6)]

        mock_client = Mock()
        mock_boto3_client.return_value = mock_client
        mock_client.execute_statement.return_value = {
            "records": [[{"stringValue": past_dates[1].strftime("%Y-%m-%d")}], [{"stringValue": past_dates[2].strftime("%Y-%m-%d")}]]
        }

        fetched_dates = {past_dates[1], past_dates[2]}
        expected_earliest_date = min(set(past_dates) - fetched_dates)
        result = get_earliest_unfetched_date("mock_aurora_arn", "mock_secret_arn", "mock_database")

        self.assertEqual(result, expected_earliest_date)

    @patch(BOTO3_CLIENT_PATH)
    def test_no_unfetched_dates(self, mock_boto3_client):
        today = datetime.today()
        past_dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(1, 6)]

        mock_client = Mock()
        mock_boto3_client.return_value = mock_client
        mock_client.execute_statement.return_value = {"records": [{"fetch_date": date} for date in past_dates]}

        result = get_earliest_unfetched_date("mock_aurora_arn", "mock_secret_arn", "mock_database")
        self.assertIsNone(result)

    @patch(BOTO3_CLIENT_PATH)
    def test_exception_on_query(self, mock_boto3_client):
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client
        mock_client.execute_statement.side_effect = Exception(DATABASE_ERROR)

        result = get_earliest_unfetched_date("mock_aurora_arn", "mock_secret_arn", "mock_database")
        self.assertIsNone(result)


class TestSetFetchStatus(unittest.TestCase):
    BOTO3_CLIENT_PATH = BASE_PATH + "boto3.client"

    @patch(BOTO3_CLIENT_PATH)
    def test_set_fetch_status_success(self, mock_boto3_client):
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client
        mock_client.execute_statement.return_value = {"update_result": "success"}

        date = "2023-01-01"
        status = "success"
        aurora_cluster_arn = "mock_aurora_cluster_arn"
        db_credentials_secret_arn = "mock_db_credentials_secret_arn"
        database = "mock_database"

        result = set_fetch_status(date, status, aurora_cluster_arn, db_credentials_secret_arn, database)
        self.assertTrue(result)

    @patch(BOTO3_CLIENT_PATH)
    def test_set_fetch_status_failure(self, mock_boto3_client):
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client
        mock_client.execute_statement.side_effect = Exception(DATABASE_ERROR)

        date = "2023-01-01"
        status = "failure"
        aurora_cluster_arn = "mock_aurora_cluster_arn"
        db_credentials_secret_arn = "mock_db_credentials_secret_arn"
        database = "mock_database"

        result = set_fetch_status(date, status, aurora_cluster_arn, db_credentials_secret_arn, database)
        self.assertFalse(result)
