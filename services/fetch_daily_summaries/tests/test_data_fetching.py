# Test data fetching functions
import unittest
import requests

from unittest.mock import patch, MagicMock, Mock
from datetime import datetime, timedelta
from services.fetch_daily_summaries.src.fetch_daily_summaries import (
    attempt_fetch_for_dates,
    handle_http_error,
    fetch_http_response,
    extract_resumption_token,
    fetch_data,
)
from xml.etree import ElementTree as ET

BASE_PATH = "services.fetch_daily_summaries.src.fetch_daily_summaries."
REQUESTS_PATH = "requests.get"


class TestAttemptFetchForDates(unittest.TestCase):
    FETCH_HTTP_RESPONSE_PATH = BASE_PATH + "fetch_http_response"
    PROCESS_FETCH_PATH = BASE_PATH + "process_fetch"
    INSERT_FETCH_STATUS_PATH = BASE_PATH + "insert_fetch_status"
    GENERATE_DATE_LIST_PATH = BASE_PATH + "generate_date_list"
    FETCH_DATA_PATH = BASE_PATH + "fetch_data"

    @patch(FETCH_DATA_PATH)
    @patch(GENERATE_DATE_LIST_PATH)
    @patch(INSERT_FETCH_STATUS_PATH)
    @patch(PROCESS_FETCH_PATH)
    def test_successful_fetch(
        self, mock_process_fetch, mock_insert_fetch_status, mock_generate_date_list, mock_fetch_data
    ):
        base_url = "mock_base_url"
        summary_set = "mock_summary_set"
        bucket_name = "mock_bucket_name"
        aurora_cluster_arn = "mock_aurora_cluster_arn"
        db_credentials_secret_arn = "mock_db_credentials_secret_arn"  # nosec
        database = "mock_database"
        today = "2023-01-02"
        earliest_unfetched_date = "2023-01-01"
        mock_date_list = ["2023-01-01", "2023-01-02"]

        mock_generate_date_list.return_value = mock_date_list
        mock_fetch_data.return_value = ["mock_xml_response_1", "mock_xml_response_2"]
        mock_process_fetch.side_effect = [True, True]

        result = attempt_fetch_for_dates(
            base_url,
            summary_set,
            bucket_name,
            aurora_cluster_arn,
            db_credentials_secret_arn,
            database,
            today,
            earliest_unfetched_date,
        )

        self.assertEqual(result, "2023-01-02")
        mock_generate_date_list.assert_called_once_with("2023-01-01", "2023-01-02")
        mock_insert_fetch_status.assert_any_call("2023-01-01", aurora_cluster_arn, db_credentials_secret_arn, database)
        mock_insert_fetch_status.assert_any_call("2023-01-02", aurora_cluster_arn, db_credentials_secret_arn, database)
        mock_process_fetch.assert_called_with(
            "2023-01-02",
            summary_set,
            bucket_name,
            aurora_cluster_arn,
            db_credentials_secret_arn,
            database,
            ["mock_xml_response_1", "mock_xml_response_2"],
        )

    @patch(FETCH_DATA_PATH)
    @patch(GENERATE_DATE_LIST_PATH)
    @patch(INSERT_FETCH_STATUS_PATH)
    @patch(PROCESS_FETCH_PATH)
    def test_fetch_failure(
        self, mock_process_fetch, mock_insert_fetch_status, mock_generate_date_list, mock_fetch_data
    ):
        base_url = "mock_base_url"
        summary_set = "mock_summary_set"
        bucket_name = "mock_bucket_name"
        aurora_cluster_arn = "mock_aurora_cluster_arn"
        db_credentials_secret_arn = "mock_db_credentials_secret_arn"  # nosec
        database = "mock_database"
        today = "2023-01-02"
        earliest_unfetched_date = "2023-01-01"
        mock_date_list = ["2023-01-01", "2023-01-02"]

        mock_generate_date_list.return_value = mock_date_list
        mock_fetch_data.return_value = ["mock_xml_response_1", "mock_xml_response_2"]
        mock_process_fetch.side_effect = [True, False]

        result = attempt_fetch_for_dates(
            base_url,
            summary_set,
            bucket_name,
            aurora_cluster_arn,
            db_credentials_secret_arn,
            database,
            today,
            earliest_unfetched_date,
        )

        if not mock_process_fetch.return_value:
            self.assertIsNone(result)
        else:
            self.assertEqual(result, "2023-01-01")

    @patch("services.fetch_daily_summaries.src.fetch_daily_summaries.logging")
    def test_no_unfetched_dates(self, mock_logging):
        base_url = "mock_base_url"
        summary_set = "mock_summary_set"
        bucket_name = "mock_bucket_name"
        aurora_cluster_arn = "mock_aurora_cluster_arn"
        db_credentials_secret_arn = "mock_db_credentials_secret_arn"  # nosec
        database = "mock_database"
        today = "2023-01-02"
        earliest_unfetched_date = None

        result = attempt_fetch_for_dates(
            base_url,
            summary_set,
            bucket_name,
            aurora_cluster_arn,
            db_credentials_secret_arn,
            database,
            today,
            earliest_unfetched_date,
        )

        self.assertIsNone(result)
        mock_logging.warning.assert_called_once()


class TestFetchData(unittest.TestCase):
    FETCH_HTTP_RESPONSE_PATH = BASE_PATH + "fetch_http_response"
    HANDLE_HTTP_ERROR_PATH = BASE_PATH + "handle_http_error"
    EXTRACT_RESUMPTION_TOKEN_PATH = BASE_PATH + "extract_resumption_token"
    TIME_SLEEP_PATH = "time.sleep"
    XML_CONTENT = "<xml>mock_content</xml>"

    @patch(BASE_PATH + "fetch_http_response")
    @patch(BASE_PATH + "extract_resumption_token")
    @patch("time.sleep", Mock())
    def test_successful_fetch_with_no_resumption_token(self, mock_extract_resumption_token, mock_fetch_http_response):
        mock_fetch_http_response.return_value = (200, self.XML_CONTENT)
        mock_extract_resumption_token.return_value = None

        result = fetch_data("mock_base_url", "2023-01-01", "mock_summary_set")

        self.assertEqual(result, [self.XML_CONTENT])

    @patch(FETCH_HTTP_RESPONSE_PATH)
    @patch(HANDLE_HTTP_ERROR_PATH)
    @patch(TIME_SLEEP_PATH, Mock())
    def test_http_error_with_backoff(self, mock_handle_http_error, mock_fetch_http_response):
        mock_fetch_http_response.side_effect = [(500, "Server Error"), (200, self.XML_CONTENT)]
        mock_handle_http_error.return_value = 1

        result = fetch_data("mock_base_url", "2023-01-01", "mock_summary_set")

        self.assertEqual(result, [self.XML_CONTENT])

    @patch(FETCH_HTTP_RESPONSE_PATH)
    @patch(EXTRACT_RESUMPTION_TOKEN_PATH)
    @patch(TIME_SLEEP_PATH, Mock())
    def test_data_fetch_with_resumption_token(self, mock_extract_resumption_token, mock_fetch_http_response):
        mock_fetch_http_response.side_effect = [(200, "<xml>mock_content_1</xml>"), (200, "<xml>mock_content_2</xml>")]
        mock_extract_resumption_token.side_effect = ["token", None]

        result = fetch_data("mock_base_url", "2023-01-01", "mock_summary_set")

        self.assertEqual(result, ["<xml>mock_content_1</xml>", "<xml>mock_content_2</xml>"])


class TestHandleHttpError(unittest.TestCase):
    LOGGING_PATH = BASE_PATH + "logging"

    @patch(LOGGING_PATH)
    def test_retry_logic_503_first_try(self, mock_logging):
        status_code = 503
        retry_count = 0
        expected_backoff_time = 30

        backoff_time = handle_http_error(status_code, "Service Unavailable", retry_count)

        self.assertEqual(backoff_time, expected_backoff_time)
        mock_logging.info.assert_called_once()

    @patch(LOGGING_PATH)
    def test_retry_logic_503_second_try(self, mock_logging):
        status_code = 503
        retry_count = 1
        expected_backoff_time = 120

        backoff_time = handle_http_error(status_code, "Service Unavailable", retry_count)

        self.assertEqual(backoff_time, expected_backoff_time)
        mock_logging.info.assert_called_once()

    @patch(LOGGING_PATH)
    def test_no_retry_logic_other_status_codes(self, mock_logging):
        status_code = 500
        retry_count = 0

        backoff_time = handle_http_error(status_code, "Server Error", retry_count)

        self.assertEqual(backoff_time, 0)
        mock_logging.assert_not_called()

    @patch(LOGGING_PATH)
    @patch(BASE_PATH + "schedule_for_later")
    def test_maintenance_response(self, mock_schedule_for_later, mock_logging):
        status_code = 503
        retry_count = 0
        response_text = "The system is under maintenance"

        backoff_time = handle_http_error(status_code, response_text, retry_count)

        self.assertEqual(backoff_time, 0)
        mock_schedule_for_later.assert_called_once()
        mock_logging.assert_not_called()


class TestFetchHttpResponse(unittest.TestCase):
    @patch(REQUESTS_PATH)
    def test_successful_response(self, mock_requests_get):
        mock_requests_get.return_value = Mock(status_code=200, text="Success")
        status_code, response_text = fetch_http_response("mock_base_url", {"param": "value"})

        self.assertEqual(status_code, 200)
        self.assertEqual(response_text, "Success")

    @patch(REQUESTS_PATH)
    def test_http_error_response(self, mock_requests_get):
        mock_requests_get.return_value = Mock(status_code=404, text="Not Found")
        status_code, response_text = fetch_http_response("mock_base_url", {"param": "value"})

        self.assertEqual(status_code, 404)
        self.assertEqual(response_text, "Not Found")

    @patch(REQUESTS_PATH)
    def test_timeout_error(self, mock_requests_get):
        mock_requests_get.side_effect = requests.exceptions.Timeout
        with self.assertRaises(requests.exceptions.Timeout):
            fetch_http_response("mock_base_url", {"param": "value"})

    @patch(REQUESTS_PATH)
    def test_connection_error(self, mock_requests_get):
        mock_requests_get.side_effect = requests.exceptions.ConnectionError
        with self.assertRaises(requests.exceptions.ConnectionError):
            fetch_http_response("mock_base_url", {"param": "value"})


class TestExtractResumptionToken(unittest.TestCase):
    @patch(BASE_PATH + "ET.fromstring")
    def test_successful_token_extraction(self, mock_fromstring):
        mock_root = MagicMock()
        mock_token_element = MagicMock()
        mock_token_element.text = "token_value"
        mock_root.find.return_value = mock_token_element
        mock_fromstring.return_value = mock_root

        token = extract_resumption_token(
            "<xml><resumptionToken>\
                                         token_value</resumptionToken></xml>"
        )

        self.assertEqual(token, "token_value")

    @patch(BASE_PATH + "ET.fromstring")
    def test_no_token_in_xml(self, mock_fromstring):
        mock_root = MagicMock()
        mock_root.find.return_value = None
        mock_fromstring.return_value = mock_root

        token = extract_resumption_token("<xml><noTokenHere /></xml>")

        self.assertIsNone(token)

    @patch(BASE_PATH + "ET.fromstring")
    def test_malformed_xml_content(self, mock_fromstring):
        mock_fromstring.side_effect = ET.ParseError
        token = extract_resumption_token("malformed xml content")

        self.assertEqual(token, "")

    def test_empty_xml_content(self):
        token = extract_resumption_token("")

        self.assertEqual(token, "")
