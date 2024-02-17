import os
from unittest.mock import ANY, MagicMock, call, patch

import pytest
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from services.fetch_daily_summaries.src.fetch_daily_summaries import (
    DataIngestionMetadata,
    calculate_mb,
    configure_request_retries,
    fetch_data,
    get_config,
    get_storage_key,
    lambda_handler,
    log_initial_info,
    logger,
)


@pytest.fixture
def event():
    """Provides a mock event object."""
    return {}


@pytest.fixture
def context():
    """Provides a mock context object."""
    return MagicMock()


@pytest.fixture
def config():
    """Provides a mock configuration dictionary."""
    return {
        "APP_NAME": "TestApp",
        "ARXIV_BASE_URL": "http://test.arxiv.org",
        "ENVIRONMENT": "test",
        "GLUE_DATABASE_NAME": "testDB",
        "GLUE_TABLE_NAME": "testTable",
        "MAX_FETCH_ATTEMPTS": "5",
        "S3_BUCKET_NAME": "testBucket",
        "S3_STORAGE_KEY_PREFIX": "testPrefix",
        "SUMMARY_SET": "cs",
    }


@patch("services.fetch_daily_summaries.src.fetch_daily_summaries.StorageManager")
@patch("services.fetch_daily_summaries.src.fetch_daily_summaries.DataIngestionMetadata")
@patch("services.fetch_daily_summaries.src.fetch_daily_summaries.fetch_data")
@patch("services.fetch_daily_summaries.src.fetch_daily_summaries.get_config")
@patch("services.fetch_daily_summaries.src.fetch_daily_summaries.datetime")
def test_lambda_handler_success(
    mock_datetime, mock_get_config, mock_fetch_data, mock_data_ingestion_metadata, mock_storage_manager, event, context
):
    mock_data_ingestion_metadata_instance = mock_data_ingestion_metadata.return_value
    mock_data_ingestion_metadata_instance.DATETIME_FORMAT = "%Y-%m-%d"
    mock_get_config.return_value = {
        "APP_NAME": "TestApp",
        "ARXIV_BASE_URL": "http://test.arxiv.org",
        "ENVIRONMENT": "test",
        "GLUE_DATABASE_NAME": "testDB",
        "GLUE_TABLE_NAME": "testTable",
        "MAX_FETCH_ATTEMPTS": 5,
        "S3_BUCKET_NAME": "testBucket",
        "S3_STORAGE_KEY_PREFIX": "testPrefix",
        "SUMMARY_SET": "cs",
    }
    mock_fetch_data.return_value = ["<xml>sample data</xml>"]
    lambda_handler(event, context)
    mock_fetch_data.assert_called_once_with(ANY, ANY, ANY, 5, ANY)


def test_get_config_with_all_variables_set():
    with patch.dict(
        os.environ,
        {
            "APP_NAME": "test_app",
            "ARXIV_BASE_URL": "https://test.arxiv.org",
            "ENVIRONMENT": "development",
            "GLUE_DATABASE_NAME": "test_glue_db",
            "GLUE_TABLE_NAME": "test_table",
            "MAX_FETCH_ATTEMPTS": "3",
            "S3_BUCKET_NAME": "test_bucket",
            "S3_STORAGE_KEY_PREFIX": "test_prefix",
            "SUMMARY_SET": "test_set",
        },
    ):
        with patch("services.fetch_daily_summaries.src.fetch_daily_summaries.logger") as mock_logger:
            config = get_config()
            assert config["APP_NAME"] == "test_app"
            assert config["ARXIV_BASE_URL"] == "https://test.arxiv.org"
            assert config["ENVIRONMENT"] == "development"
            assert int(config["MAX_FETCH_ATTEMPTS"]) == 3
            mock_logger.debug.assert_called_once()


def test_get_config_missing_environment_variable():
    incomplete_env = {
        "APP_NAME": "test_app",
    }
    with patch.dict(os.environ, incomplete_env, clear=True):
        with patch("services.fetch_daily_summaries.src.fetch_daily_summaries.logger") as mock_logger:
            with pytest.raises(KeyError):
                get_config()
            mock_logger.error.assert_called_once()


@patch.dict(
    "os.environ", {"AWS_LAMBDA_LOG_GROUP_NAME": "test_log_group", "AWS_LAMBDA_LOG_STREAM_NAME": "test_log_stream"}
)
@patch.object(logger, "debug")
def test_log_initial_info_full(mock_logger_debug):
    event = {"key": "value"}
    log_initial_info(event)

    mock_logger_debug.assert_any_call(
        "Log variables",
        method="fetch_daily_summaries.log_initial_info",
        log_group="test_log_group",
        log_stream="test_log_stream",
    )
    mock_logger_debug.assert_any_call("Running on", method="fetch_daily_summaries.log_initial_info", platform="AWS")
    mock_logger_debug.assert_any_call(
        "Event received", method="fetch_daily_summaries.log_initial_info", trigger_event=event
    )


@patch.dict("os.environ", {}, clear=True)
@patch.object(logger, "debug")
def test_log_initial_info_missing_env(mock_logger_debug):
    event = {"key": "value"}
    log_initial_info(event)

    mock_logger_debug.assert_any_call(
        "Running on", method="fetch_daily_summaries.log_initial_info", platform="CI/CD or local"
    )
    mock_logger_debug.assert_any_call(
        "Event received", method="fetch_daily_summaries.log_initial_info", trigger_event=event
    )


def load_test_data(filename):
    with open(filename, "r") as file:
        return file.read()


def mock_session_get_success(url, params, timeout):
    class MockResponse:
        def __init__(self, text, status_code, request_url):
            self.text = text
            self.status_code = status_code
            self.content = text.encode("utf-8")
            self.request = MagicMock()
            self.request.url = request_url

        def raise_for_status(self):
            if self.status_code != 200:
                raise requests.exceptions.HTTPError()

    test_data = load_test_data(os.path.join(os.path.dirname(__file__), "resources", "test_arxiv_data.xml"))
    return MockResponse(test_data, 200, "http://test.arxiv.org")


@pytest.fixture
def metadata():
    metadata = DataIngestionMetadata()
    metadata.app_name = "TestApp"
    metadata.date_time = "2024-02-17T12:00:00Z"
    metadata.environment = "test"
    metadata.function_name = "lambda_handler"
    return metadata


def mock_session_get_sequential(*args, **kwargs):
    class MockResponse:
        def __init__(self, content, status_code, request_url):
            self.content = content
            self.status_code = status_code
            self.request = MagicMock(url=request_url)

        def raise_for_status(self):
            if self.status_code != 200:
                raise requests.exceptions.HTTPError(f"Status code: {self.status_code}")

        @property
        def text(self):
            return self.content.decode("utf-8")

    if "resumptionToken" in kwargs["params"]:
        followup_data = "<followup>Follow-up data</followup>"
        return MockResponse(followup_data.encode("utf-8"), 200, "http://test.arxiv.org/followup")
    else:
        test_data_path = os.path.join(os.path.dirname(__file__), "resources", "test_arxiv_data.xml")
        with open(test_data_path, "r") as file:
            test_data = file.read()
        return MockResponse(test_data.encode("utf-8"), 200, "http://test.arxiv.org/initial")


@patch("requests.Session.get", side_effect=mock_session_get_sequential)
def test_fetch_data_success_with_sequential(mock_get, metadata):
    base_url = "http://test.arxiv.org"
    from_date = "2024-02-17"
    summary_set = "cs"
    max_fetches = 2

    xml_data_list = fetch_data(base_url, from_date, summary_set, max_fetches, metadata)

    assert len(xml_data_list) == 2, "Should fetch data twice, including with resumptionToken."
    assert "<followup>Follow-up data</followup>" in xml_data_list[1], "Follow-up data does not match expected."

    initial_call_params = {"verb": "ListRecords", "set": summary_set, "metadataPrefix": "oai_dc", "from": from_date}
    followup_call_params = {"verb": "ListRecords", "resumptionToken": "6960524|1001"}

    assert mock_get.call_args_list[0][1]["params"] == initial_call_params, "Initial fetch parameters incorrect."
    assert mock_get.call_args_list[1][1]["params"] == followup_call_params, "Follow-up fetch parameters incorrect."


@patch("services.fetch_daily_summaries.src.fetch_daily_summaries.HTTPAdapter")
@patch("services.fetch_daily_summaries.src.fetch_daily_summaries.Retry")
@patch("services.fetch_daily_summaries.src.fetch_daily_summaries.requests.Session")
def test_configure_request_retries(mock_session_cls, mock_retry_cls, mock_http_adapter_cls):
    mock_retry_instance = MagicMock(spec=Retry)
    mock_retry_cls.return_value = mock_retry_instance

    mock_http_adapter_instance = MagicMock(spec=HTTPAdapter)
    mock_http_adapter_cls.return_value = mock_http_adapter_instance

    mock_session = MagicMock(spec=requests.Session)
    mock_session.mount = MagicMock()
    mock_session_cls.return_value = mock_session

    session = configure_request_retries()

    mock_retry_cls.assert_called_once_with(
        total=5,
        backoff_factor=1,
        status_forcelist=[503],
        respect_retry_after_header=True,
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,
    )

    expected_http_adapter_calls = [call(max_retries=mock_retry_instance), call(max_retries=mock_retry_instance)]
    mock_http_adapter_cls.assert_has_calls(expected_http_adapter_calls, any_order=True)

    expected_mount_calls = [call("http://", mock_http_adapter_instance), call("https://", mock_http_adapter_instance)]
    mock_session.mount.assert_has_calls(expected_mount_calls, any_order=True)

    assert session is mock_session


def test_calculate_mb():
    assert calculate_mb(1024 * 1024) == 1.0
    assert calculate_mb(1024 * 1024 * 1.5) == 1.5
    assert calculate_mb(512) == 0.0
    assert calculate_mb(1024 * 1024 * 1024) == 1024.0


@patch("services.fetch_daily_summaries.src.fetch_daily_summaries.time.strftime")
def test_get_storage_key_valid_config(mock_strftime):
    mock_strftime.return_value = "2024-02-17"
    config = {"S3_STORAGE_KEY_PREFIX": "test_prefix"}
    expected_key = "test_prefix/2024-02-17.json"
    assert get_storage_key(config) == expected_key


@patch("services.fetch_daily_summaries.src.fetch_daily_summaries.logger")
def test_get_storage_key_missing_config(mock_logger):
    config = {}
    with pytest.raises(ValueError) as excinfo:
        get_storage_key(config)
    assert "Config is required" in str(excinfo.value)
    mock_logger.error.assert_called_once_with("Config is required", method="fetch_daily_summaries.get_storage_key")
