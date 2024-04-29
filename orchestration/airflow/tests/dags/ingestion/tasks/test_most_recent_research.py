import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import neo4j
import neo4j.time
import pytest

from orchestration.airflow.dags.ingestion.tasks.most_recent_research_task import (
    run,
    get_config,
    get_earliest_date,
)
from orchestration.airflow.dags.shared.utils.constants import (
    ARXIV_BASE_URL,
    ARXIV_INGESTION_DAY_SPAN,
    ARXIV_RESEARCH_DATE_FORMAT,
    ARXIV_SETS,
    AWS_REGION,
    AWS_SECRETS_NEO4J_CREDENTIALS,
    AWS_SECRETS_NEO4J_PASSWORD,
    AWS_SECRETS_NEO4J_USERNAME,
    DATA_BUCKET,
    DATA_INGESTION_KEY_PREFIX,
    ENVIRONMENT_NAME,
    INGESTION_EARLIEST_DATE,
    NEO4J_CONNECTION_RETRIES,
    NEO4J_CONNECTION_RETRIES_DEFAULT,
    NEO4J_PASSWORD,
    NEO4J_URI,
    NEO4J_USERNAME,
    RESEARCH_RECORD_DATE,
)


@pytest.fixture
def context():
    return {
        "dag": MagicMock(),
        "ds": "2021-01-01",
        "run_id": "test_run_id",
    }


@pytest.fixture
def mock_graph_driver():
    with patch("orchestration.airflow.dags.ingestion.tasks.most_recent_research_task.GraphDatabase.driver") as mock:
        yield mock


@pytest.fixture
def mock_logger():
    with patch("orchestration.airflow.dags.ingestion.tasks.most_recent_research_task") as mock:
        yield mock


@pytest.fixture
def config():
    """Sample config fixture."""
    return {
        ARXIV_BASE_URL: "http://example.com",
        ARXIV_INGESTION_DAY_SPAN: "1",
        ARXIV_SETS: '["cs"]',
        AWS_REGION: "us-east-1",
        DATA_BUCKET: "my-test-bucket",
        DATA_INGESTION_KEY_PREFIX: "data/prefix",
        ENVIRONMENT_NAME: "test",
        NEO4J_CONNECTION_RETRIES: "5",
        NEO4J_PASSWORD: "password",
        NEO4J_URI: "bolt://localhost:7687",
        NEO4J_USERNAME: "username",
    }


@patch("orchestration.airflow.dags.ingestion.tasks.most_recent_research_task.logger")
@patch("orchestration.airflow.dags.ingestion.tasks.most_recent_research_task.get_config", return_value=config)
@patch("orchestration.airflow.dags.ingestion.tasks.most_recent_research_task.get_earliest_date", return_value="2021-01-01")
def test_run_should_push_date_to_xcom(get_earliest_date, get_config, logger, context):
    context["ti"] = MagicMock()
    context["ti"].xcom_push = MagicMock()
    run(**context)
    assert context.get("ti").xcom_push.called
    assert context.get("ti").xcom_push.call_args.kwargs == {"key": INGESTION_EARLIEST_DATE, "value": "2021-01-01"}


@patch(
    "orchestration.airflow.dags.ingestion.tasks.most_recent_research_task.os.environ",
    {
        ARXIV_INGESTION_DAY_SPAN: "1",
        AWS_REGION: "us-east-1",
        AWS_SECRETS_NEO4J_CREDENTIALS: "neo4j",
        AWS_SECRETS_NEO4J_PASSWORD: "neo4j_password",
        AWS_SECRETS_NEO4J_USERNAME: "neo4j_username",
        ENVIRONMENT_NAME: "test",
        NEO4J_CONNECTION_RETRIES: "3",
        NEO4J_CONNECTION_RETRIES_DEFAULT: "5",
        NEO4J_PASSWORD : "password",
        NEO4J_URI: "bolt://localhost:7687",
        NEO4J_USERNAME: "username",
    },
)
@patch("orchestration.airflow.dags.ingestion.tasks.most_recent_research_task.get_aws_secrets")
def test_config_should_parse_env_vars(mock_get_aws_secrets):
    get_config()
    mock_get_aws_secrets.assert_called_once_with("neo4j-credentials", "us-east-1", "test")
    mock_get_aws_secrets.return_value = {
        AWS_SECRETS_NEO4J_PASSWORD: "password",
        AWS_SECRETS_NEO4J_USERNAME: "username",
    }
    result = get_config()
    assert result == {
        ARXIV_INGESTION_DAY_SPAN: 1,
        AWS_REGION: "us-east-1",
        ENVIRONMENT_NAME: "test",
        NEO4J_CONNECTION_RETRIES: 3,
        NEO4J_PASSWORD: "password",
        NEO4J_URI: "bolt://localhost:7687",
        NEO4J_USERNAME: "username",
    }


@patch("orchestration.airflow.dags.ingestion.tasks.most_recent_research_task.get_storage_key_datetime")
def test_get_earliest_date_defaults(mock_storage_key_datetime, config, mock_graph_driver):
    mock_storage_key_datetime.return_value = datetime(2023, 1, 1, 12, 0)
    mock_session = MagicMock()
    mock_graph_driver.return_value.__enter__.return_value = mock_session
    mock_session.execute_query.return_value = ([], None, None)

    result = get_earliest_date(config)
    expected_date = (datetime(2023, 1, 1).date() - timedelta(days=1)).strftime(ARXIV_RESEARCH_DATE_FORMAT)

    assert result == expected_date


@patch("orchestration.airflow.dags.ingestion.tasks.most_recent_research_task.get_storage_key_datetime")
def test_get_earliest_date_with_records(mock_storage_key_datetime, config, mock_graph_driver):
    mock_storage_key_datetime.return_value = datetime(2023, 1, 1, 12, 0)
    mock_session = MagicMock()
    mock_graph_driver.return_value.__enter__.return_value = mock_session

    mock_record = MagicMock()
    mock_record.data.return_value = {"r": {RESEARCH_RECORD_DATE: neo4j.time.DateTime(2023, 1, 10)}}
    mock_session.execute_query.return_value = ([mock_record], None, None)

    result = get_earliest_date(config)
    expected_date = (datetime(2023, 1, 10) + timedelta(days=1)).strftime(ARXIV_RESEARCH_DATE_FORMAT)

    assert result == expected_date
