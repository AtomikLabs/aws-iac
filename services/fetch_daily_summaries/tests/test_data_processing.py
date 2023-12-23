# Test file for fetch_daily_summaries data processing functions
import unittest
from datetime import date, datetime, timedelta
from unittest.mock import patch, MagicMock
from services.fetch_daily_summaries.src.fetch_daily_summaries import (
    log_initial_info,
    calculate_from_date,
    generate_date_list,
    schedule_for_later,
    process_fetch,
    upload_to_s3,
)

BASE_PATH = "services.fetch_daily_summaries.src.fetch_daily_summaries."


class TestLogInitialInfo(unittest.TestCase):
    LOGGING_PATH = BASE_PATH + "logging"
    START_MESSAGE = "Starting to fetch arXiv daily summaries"

    def setUp(self):
        self.mock_logger = MagicMock()
        self.patcher = patch(TestLogInitialInfo.LOGGING_PATH, self.mock_logger)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_log_initial_info_with_valid_event(self):
        event = {"key": "value"}
        log_initial_info(event)
        self.mock_logger.info.assert_any_call(f"Received event: {event}")
        self.mock_logger.info.assert_any_call(TestLogInitialInfo.START_MESSAGE)

    def test_log_initial_info_with_empty_event(self):
        event = {}
        log_initial_info(event)
        self.mock_logger.info.assert_any_call(f"Received event: {event}")
        self.mock_logger.info.assert_any_call(TestLogInitialInfo.START_MESSAGE)

    def test_log_initial_info_with_none_event(self):
        event = None
        log_initial_info(event)
        self.mock_logger.info.assert_any_call(f"Received event: {event}")
        self.mock_logger.info.assert_any_call(TestLogInitialInfo.START_MESSAGE)

    def test_log_initial_info_with_unusual_event(self):
        event = "Some event"
        log_initial_info(event)
        self.mock_logger.info.assert_any_call(f"Received event: {event}")
        self.mock_logger.info.assert_any_call(TestLogInitialInfo.START_MESSAGE)


class TestCalculateFromDate(unittest.TestCase):
    @patch("services.fetch_daily_summaries.src.fetch_daily_summaries.datetime")
    def test_calculate_from_date(self, mock_datetime):
        mock_today = datetime(2023, 1, 2)
        mock_datetime.today.return_value = mock_today
        expected_date = mock_today - timedelta(days=1)
        result = calculate_from_date()
        self.assertEqual(result, expected_date.date())

    @patch("services.fetch_daily_summaries.src.fetch_daily_summaries.datetime")
    def test_calculate_from_date_leap_year(self, mock_datetime):
        mock_today = datetime(2024, 2, 29)
        mock_datetime.today.return_value = mock_today
        expected_date = mock_today - timedelta(days=1)
        result = calculate_from_date()
        self.assertEqual(result, expected_date.date())

    @patch("services.fetch_daily_summaries.src.fetch_daily_summaries.datetime")
    def test_calculate_from_date_year_change(self, mock_datetime):
        mock_today = datetime(2023, 1, 1)
        mock_datetime.today.return_value = mock_today
        expected_date = mock_today - timedelta(days=1)
        result = calculate_from_date()
        self.assertEqual(result, expected_date.date())


class TestGenerateDateList(unittest.TestCase):
    def test_generate_normal_date_range(self):
        start_date = date(2023, 1, 1)
        end_date = date(2023, 1, 5)
        expected_result = [date(2023, 1, 1), date(2023, 1, 2), date(2023, 1, 3), date(2023, 1, 4), date(2023, 1, 5)]
        self.assertEqual(generate_date_list(start_date, end_date), expected_result)

    def test_generate_single_date_range(self):
        start_date = date(2023, 1, 1)
        end_date = date(2023, 1, 1)
        expected_result = [date(2023, 1, 1)]
        self.assertEqual(generate_date_list(start_date, end_date), expected_result)

    def test_generate_date_range_in_future(self):
        start_date = date(2023, 1, 1)
        end_date = date(2023, 1, 10)
        expected_result = [
            date(2023, 1, 1),
            date(2023, 1, 2),
            date(2023, 1, 3),
            date(2023, 1, 4),
            date(2023, 1, 5),
            date(2023, 1, 6),
            date(2023, 1, 7),
            date(2023, 1, 8),
            date(2023, 1, 9),
            date(2023, 1, 10),
        ]
        self.assertEqual(generate_date_list(start_date, end_date), expected_result)

    def test_generate_date_range_with_end_date_before_start_date(self):
        start_date = date(2023, 1, 5)
        end_date = date(2023, 1, 1)
        with self.assertRaises(ValueError):
            generate_date_list(start_date, end_date)


class TestScheduleForLater(unittest.TestCase):
    BOTO3_CLIENT_PATH = BASE_PATH + "boto3.client"
    OS_ENVIRON_PATH = BASE_PATH + "os.environ"

    @patch(BOTO3_CLIENT_PATH)
    @patch.dict(
        OS_ENVIRON_PATH,
        {"AWS_REGION": "us-east-1", "AWS_ACCOUNT_ID": "123456789012", "AWS_LAMBDA_FUNCTION_NAME": "testFunction"},
    )
    def test_successful_scheduling(self, mock_boto3):
        mock_client = MagicMock()
        mock_boto3.return_value = mock_client

        schedule_for_later()

        mock_client.put_rule.assert_called_once()
        mock_client.put_targets.assert_called_once()

    @patch(BOTO3_CLIENT_PATH)
    @patch.dict(
        OS_ENVIRON_PATH,
        {"AWS_REGION": "us-east-1", "AWS_ACCOUNT_ID": "123456789012", "AWS_LAMBDA_FUNCTION_NAME": "testFunction"},
    )
    def test_scheduling_failure_due_to_client_error(self, mock_boto3):
        mock_client = MagicMock()
        mock_client.put_rule.side_effect = Exception("AWS client error")
        mock_boto3.return_value = mock_client

        with self.assertRaises(Exception):
            schedule_for_later()

    @patch(BOTO3_CLIENT_PATH)
    def test_scheduling_failure_due_to_missing_environment_variables(self, mock_boto3):
        with self.assertRaises(KeyError):
            schedule_for_later()


class TestProcessFetch(unittest.TestCase):
    UPLOAD_TO_S3_PATH = BASE_PATH + "upload_to_s3"
    SET_FETCH_STATUS_PATH = BASE_PATH + "set_fetch_status"

    def create_test_xml(self, date):
        return f"""
        </dc:description>
        <dc:description>Comment: Example Comment</dc:description>
        <dc:date>{date}</dc:date>
        <dc:type>text</dc:type>
        <dc:identifier>http://example.com/{date}</dc:identifier>
        </oai_dc:dc>
        </metadata>
        </record>
        <record>
        """

    @patch(UPLOAD_TO_S3_PATH)
    @patch(SET_FETCH_STATUS_PATH)
    def test_successful_fetch(self, mock_set_fetch_status, mock_upload_to_s3):
        test_xml = self.create_test_xml("2023-01-01")
        success = process_fetch(
            date(2023, 1, 1),
            "summary_set",
            "bucket_name",
            "aurora_cluster_arn",
            "db_credentials_secret_arn",
            "database",
            [test_xml],
        )
        self.assertTrue(success)
        mock_upload_to_s3.assert_called_once()
        mock_set_fetch_status.assert_called_with(
            date(2023, 1, 1), "success", "aurora_cluster_arn", "db_credentials_secret_arn", "database"
        )

    @patch(SET_FETCH_STATUS_PATH)
    def test_unsuccessful_fetch(self, mock_set_fetch_status):
        test_xml = self.create_test_xml("2023-01-02")
        success = process_fetch(
            date(2023, 1, 1),
            "summary_set",
            "bucket_name",
            "aurora_cluster_arn",
            "db_credentials_secret_arn",
            "database",
            [test_xml],
        )
        self.assertFalse(success)
        mock_set_fetch_status.assert_called_with(
            date(2023, 1, 1), "failure", "aurora_cluster_arn", "db_credentials_secret_arn", "database"
        )

    @patch(SET_FETCH_STATUS_PATH)
    def test_fetch_with_missing_parameters(self, mock_set_fetch_status):
        with self.assertRaises(AttributeError):
            process_fetch(
                None,
                "summary_set",
                "bucket_name",
                "aurora_cluster_arn",
                "db_credentials_secret_arn",
                "database",
                ["<xml>...</xml>"],
            )

    @patch(SET_FETCH_STATUS_PATH)
    def test_fetch_with_invalid_data_format(self, mock_set_fetch_status):
        success = process_fetch(
            date(2023, 1, 1),
            "summary_set",
            "bucket_name",
            "aurora_cluster_arn",
            "db_credentials_secret_arn",
            "database",
            ["invalid data format"],
        )
        self.assertFalse(success)
        mock_set_fetch_status.assert_called_with(
            date(2023, 1, 1), "failure", "aurora_cluster_arn", "db_credentials_secret_arn", "database"
        )

    @patch(SET_FETCH_STATUS_PATH)
    def test_fetch_handling_database_interaction_error(self, mock_set_fetch_status):
        mock_set_fetch_status.side_effect = Exception("Database error")
        with self.assertRaises(Exception) as context:
            process_fetch(
                date(2023, 1, 1),
                "summary_set",
                "bucket_name",
                "aurora_cluster_arn",
                "db_credentials_secret_arn",
                "database",
                ["<xml><dc:date>2023-01-01</dc:date></xml>"],
            )
        self.assertTrue("Database error" in str(context.exception))


class TestUploadToS3(unittest.TestCase):
    S3_CLIENT_PATH = BASE_PATH + "boto3.client"

    @patch(S3_CLIENT_PATH)
    def test_successful_upload(self, mock_s3_client):
        mock_client = MagicMock()
        mock_s3_client.return_value = mock_client
        xml_responses = ["<xml>response1</xml>", "<xml>response2</xml>"]

        upload_to_s3("test-bucket", date(2023, 1, 1), "summary1", xml_responses)

        self.assertEqual(mock_client.put_object.call_count, len(xml_responses))
        for idx, call in enumerate(mock_client.put_object.call_args_list):
            _, kwargs = call
            self.assertEqual(kwargs["Bucket"], "test-bucket")
            self.assertEqual(kwargs["Key"], f"arxiv/summary1-2023-01-01-{idx}.xml")
            self.assertEqual(kwargs["Body"], xml_responses[idx])

    @patch(S3_CLIENT_PATH)
    def test_upload_with_empty_responses(self, mock_s3_client):
        mock_client = MagicMock()
        mock_s3_client.return_value = mock_client

        upload_to_s3("test-bucket", date(2023, 1, 1), "summary1", [])

        mock_client.put_object.assert_not_called()

    @patch(S3_CLIENT_PATH)
    def test_upload_exception_handling(self, mock_s3_client):
        mock_client = MagicMock()
        mock_client.put_object.side_effect = Exception("S3 Upload Error")
        mock_s3_client.return_value = mock_client
        xml_responses = ["<xml>response1</xml>"]

        with self.assertRaises(Exception) as context:
            upload_to_s3("test-bucket", date(2023, 1, 1), "summary1", xml_responses)

        self.assertEqual(str(context.exception), "S3 Upload Error")
