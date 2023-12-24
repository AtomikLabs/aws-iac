# Test file for fetch_daily_summaries data processing functions
import unittest
from datetime import date, datetime, timedelta
from unittest.mock import patch, MagicMock
from services.fetch_daily_summaries.src.fetch_daily_summaries import (
    log_initial_info,
    calculate_from_date,
    generate_date_list,
    schedule_for_later,
    update_research_fetch_status,
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

    def create_test_xml(self, date_str):
        return (
            "<record><header><identifier>oai:arXiv.org:2312.13495</identifier>"
            "<datestamp>2023-12-22</datestamp><setSpec>cs</setSpec></header>"
            "<metadata>"
            '<oai_dc:dc xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/oai_dc/ '
            'http://www.openarchives.org/OAI/2.0/oai_dc.xsd">'
            "<dc:title>Decoupling Representation and Knowledge for Few-Shot Intent Classification and Slot Filling</dc:title>"
            "<dc:creator>Han, Jie</dc:creator><dc:creator>Zou, Yixiong</dc:creator>"
            "<dc:creator>Wang, Haozhao</dc:creator><dc:creator>Wang, Jun</dc:creator>"
            "<dc:creator>Liu, Wei</dc:creator><dc:creator>Wu, Yao</dc:creator>"
            "<dc:creator>Zhang, Tao</dc:creator><dc:creator>Li, Ruixuan</dc:creator>"
            "<dc:subject>Computer Science - Computation and Language</dc:subject>"
            "<dc:subject>Computer Science - Artificial Intelligence</dc:subject>"
            "<dc:description> Few-shot intent classification and slot filling are important but challenging tasks due to the scarcity of finely labeled data. Therefore, current works first train a model on source domains with sufficiently labeled data, and then transfer the model to target domains where only rarely labeled data is available. However, experience transferring as a whole usually suffers from gaps that exist among source domains and target domains. For instance, transferring domain-specific-knowledge-related experience is difficult. To tackle this problem, we propose a new method that explicitly decouples the transferring of general-semantic-representation-related experience and the domain-specific-knowledge-related experience. Specifically, for domain-specific-knowledge-related experience, we design two modules to capture intent-slot relation and slot-slot relation respectively. Extensive experiments on Snips and FewJoint datasets show that our method achieves state-of-the-art performance. The method improves the joint accuracy metric from 27.72% to 42.20% in the 1-shot setting, and from 46.54% to 60.79% in the 5-shot setting. </dc:description>"
            "<dc:description>Comment: 9 pages, 4 figures</dc:description>"
            "<dc:date>" + date_str + "</dc:date>"
            "<dc:type>text</dc:type>"
            "<dc:identifier>http://arxiv.org/abs/2312.13495</dc:identifier>"
            "</oai_dc:dc>"
            "</metadata>"
            "</record>"
        )

    @patch(UPLOAD_TO_S3_PATH)
    @patch(SET_FETCH_STATUS_PATH)
    def test_successful_fetch(self, mock_set_fetch_status, mock_upload_to_s3):
        test_xml = self.create_test_xml("2023-01-01")
        success = update_research_fetch_status(
            date(2023, 1, 1),
            "summary_set",
            "bucket_name",
            "aurora_cluster_arn",
            "db_credentials_secret_arn",
            "database",
            [test_xml],
        )
        self.assertTrue(success)
        mock_set_fetch_status.assert_called_with(
            date(2023, 1, 1), "success", "aurora_cluster_arn", "db_credentials_secret_arn", "database"
        )

    @patch(SET_FETCH_STATUS_PATH)
    def test_unsuccessful_fetch(self, mock_set_fetch_status):
        test_xml = self.create_test_xml("2023-01-02")
        success = update_research_fetch_status(
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
            update_research_fetch_status(
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
        success = update_research_fetch_status(
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
            update_research_fetch_status(
                date(2023, 1, 1),
                "summary_set",
                "bucket_name",
                "aurora_cluster_arn",
                "db_credentials_secret_arn",
                "database",
                ["<xml><dc:date>2023-01-01</dc:date></xml>"],
            )
        self.assertTrue("Database error" in str(context.exception))
