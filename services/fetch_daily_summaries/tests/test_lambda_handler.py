import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest

from services.fetch_daily_summaries.src.fetch_daily_summaries.lambda_handler import lambda_handler, fetch_data, get_config, log_initial_info, get_storage_key

@pytest.fixture
def event():
    """Sample AWS event fixture."""
    return {}

@pytest.fixture
def context():
    """Sample AWS context fixture, can be expanded as needed."""
    return MagicMock()

@pytest.fixture
def config():
    """Sample config fixture."""
    return {
        "APP_NAME": "test_app",
        "ARXIV_BASE_URL": "http://example.com",
        "ARXIV_SUMMARY_SET": "cs",
        "DATA_BUCKET": "my-test-bucket",
        "DATA_INGESTION_KEY_PREFIX": "data/prefix",
        "ENVIRONMENT_NAME": "test",
        "MAX_RETRIES": "3",
        "NEO4J_PASSWORD": "password",
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USERNAME": "username",
        "SERVICE_NAME": "test_service",
        "SERVICE_VERSION": "1.0"
    }

@patch("services.fetch_daily_summaries.src.fetch_daily_summaries.lambda_handler.logger")
def test_log_initial_info(mock_logger, event):
    log_initial_info(event)
    mock_logger.debug.assert_called()

@patch("services.fetch_daily_summaries.src.fetch_daily_summaries.lambda_handler.os.environ", {"MAX_RETRIES": "3", "ARXIV_BASE_URL": "http://example.com", "ARXIV_SUMMARY_SET": "cs", "DATA_BUCKET": "my-test-bucket", "DATA_INGESTION_KEY_PREFIX": "data/prefix", "ENVIRONMENT": "test", "NEO4J_PASSWORD": "password", "NEO4J_URI": "bolt://localhost:7687", "NEO4J_USERNAME": "username", "SERVICE_NAME": "test_service", "SERVICE_VERSION": "1.0", "APP_NAME": "test_app"})
def test_get_config():
    expected = {
        "MAX_RETRIES": 3,
        "ARXIV_BASE_URL": "http://example.com",
        "ARXIV_SUMMARY_SET": "cs",
        "DATA_BUCKET": "my-test-bucket",
        "DATA_INGESTION_KEY_PREFIX": "data/prefix",
        "ENVIRONMENT": "test",
        "NEO4J_PASSWORD": "password",
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USERNAME": "username",
        "SERVICE_NAME": "test_service",
        "SERVICE_VERSION": "1.0",
        "APP_NAME": "test_app"
    }
    assert get_config() == expected

@patch("services.fetch_daily_summaries.src.fetch_daily_summaries.lambda_handler.requests.Session")
def test_fetch_data(mock_session):
    mock_response = MagicMock()
    mock_response.text = "<xml>data</xml>"
    mock_response.content = b"<xml>data</xml>"
    mock_response.raise_for_status = MagicMock()
    mock_session.return_value.get.return_value = mock_response

    base_url = "http://example.com"
    from_date = (datetime.today() - timedelta(days=5)).strftime("%Y-%m-%d")
    set_name = "cs"
    max_fetches = 1

    result = fetch_data(base_url, from_date, set_name, max_fetches)
    assert len(result) == 1
    assert result[0] == "<xml>data</xml>"

@patch("services.fetch_daily_summaries.src.fetch_daily_summaries.lambda_handler.datetime")
@patch("services.fetch_daily_summaries.src.fetch_daily_summaries.lambda_handler.StorageManager")
def test_lambda_handler_success(mock_storage_manager, mock_datetime, event, context, config):
    mock_datetime.today.return_value = datetime(2023, 1, 1)
    mock_datetime.strptime.return_value = datetime(2023, 1, 1)
    with patch("services.fetch_daily_summaries.src.fetch_daily_summaries.lambda_handler.get_config", return_value=config), \
         patch("services.fetch_daily_summaries.src.fetch_daily_summaries.lambda_handler.fetch_data", return_value=["<xml>data</xml>"]), \
         patch("services.fetch_daily_summaries.src.fetch_daily_summaries.lambda_handler.get_storage_key", return_value="key"):
        response = lambda_handler(event, context)
        assert response["statusCode"] == 200
        assert json.loads(response["body"]) == {"message": "Success"}

@patch("services.fetch_daily_summaries.src.fetch_daily_summaries.lambda_handler.logger")
def test_lambda_handler_exception(mock_logger, event, context):
    with patch("services.fetch_daily_summaries.src.fetch_daily_summaries.lambda_handler.get_config", side_effect=Exception("Test exception")):
        response = lambda_handler(event, context)
        assert response["statusCode"] == 500
        assert json.loads(response["body"]) == {"message": "Internal Server Error"}
