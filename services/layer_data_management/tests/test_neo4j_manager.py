from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest
import unittest
from neo4j.exceptions import ServiceUnavailable

from services.layer_data_management.src.layer_data_management.neo4j_manager import Neo4jDatabase

URI = "neo4j://localhost:7687"
USERNAME = "neo4j"
PASSWORD = "password"
ARXIV_NODE_RESPONSE = {"uuid": "test-uuid", "name": "arXiv", "url": "http://arxiv.org", "description": "A description"}
ARXIV_URL = "http://arxiv.org"
ARXIV_RAW_DATA_RESPONSE = {
    "d": {
        "uuid": "test-uuid",
        "date_from": date(2024, 3, 18),
        "date_to": date(2024, 3, 18),
        "description": "test-description",
        "format": "test-format",
        "storage_uri": "test-storage-uri",
        "size_bytes": 1,
    },
    "dop": {
        "uuid": "test-uuid",
        "date": datetime(2024, 3, 18, 0, 0, 0, 0),
        "method_name": "test-method-name",
        "method_version": "test-method-version",
        "name": "test-name",
    },
    "s": {"uuid": "test-uuid"},
}
ARXIV_RAW_DATA_PARAMS = {
    "date_from": date(2024, 3, 18),
    "date_to": date(2024, 3, 18),
    "date_obtained": datetime(2024, 3, 18, 0, 0, 0, 0),
    "method_name": "test-method",
    "method_version": "test-version",
    "size_bytes": 256,
    "bucket_name": "test-bucket",
    "storage_uri": "test-uri",
}


@pytest.fixture
def neo4j_db():
    return Neo4jDatabase(URI, USERNAME, PASSWORD)


def test_neo4j_database_manager():
    db = Neo4jDatabase(URI, USERNAME, PASSWORD)
    assert db is not None
    assert db.uri == URI
    assert db.username == USERNAME
    assert db.password == PASSWORD


def test_neo4j_database_manager_should_raise_exception_with_missing_params():
    uri = None
    username = None
    password = None
    param_missing_message = "Password, URI, and user are required."
    with pytest.raises(Exception) as e:
        Neo4jDatabase(uri, USERNAME, PASSWORD)
    assert str(e.value) == param_missing_message
    with pytest.raises(Exception) as e:
        Neo4jDatabase(URI, username, PASSWORD)
    assert str(e.value) == param_missing_message
    with pytest.raises(Exception) as e:
        Neo4jDatabase(URI, USERNAME, password)
    assert str(e.value) == param_missing_message


def test_neo4j_database_manager_should_raise_exception_with_wrong_param_type():
    param_wrong_type_message = "Password, URI, and user must be strings."
    with pytest.raises(Exception) as e:
        Neo4jDatabase(1, USERNAME, PASSWORD)
    assert str(e.value) == param_wrong_type_message
    with pytest.raises(Exception) as e:
        Neo4jDatabase(URI, 1, PASSWORD)
    assert str(e.value) == param_wrong_type_message
    with pytest.raises(Exception) as e:
        Neo4jDatabase(URI, USERNAME, 1)
    assert str(e.value) == param_wrong_type_message


@patch("services.layer_data_management.src.layer_data_management.neo4j_manager.GraphDatabase.driver")
def test_missing_credentials(mock_driver):
    with pytest.raises(ValueError):
        db = Neo4jDatabase(URI, USERNAME, PASSWORD)
        db.uri = None
        db.check_arxiv_node_exists()
    with pytest.raises(ValueError):
        db.uri = URI
        db.username = None
        db.check_arxiv_node_exists()
    with pytest.raises(ValueError):
        db.username = USERNAME
        db.password = None
        db.check_arxiv_node_exists()


@patch("services.layer_data_management.src.layer_data_management.neo4j_manager.GraphDatabase.driver")
def test_check_arxiv_node_exists_success(mock_driver, neo4j_db):
    mock_driver.return_value.__enter__.return_value.execute_query.return_value = (
        [MagicMock(data=lambda: ARXIV_NODE_RESPONSE)],
        None,
        None,
    )
    result = neo4j_db.check_arxiv_node_exists()
    assert result == ARXIV_NODE_RESPONSE


@patch("services.layer_data_management.src.layer_data_management.neo4j_manager.GraphDatabase.driver")
def test_check_arxiv_node_not_found(mock_driver, neo4j_db):
    mock_driver.return_value.__enter__.return_value.execute_query.return_value = ([], None, None)
    result = neo4j_db.check_arxiv_node_exists()
    assert result == {}


@patch("services.layer_data_management.src.layer_data_management.neo4j_manager.GraphDatabase.driver")
def test_check_arxiv_node_multiple_arxiv_nodes_found(mock_driver, neo4j_db):
    mock_driver.return_value.__enter__.return_value.execute_query.return_value = (
        [MagicMock(), MagicMock()],
        None,
        None,
    )
    with pytest.raises(ValueError):
        neo4j_db.check_arxiv_node_exists()


@patch("services.layer_data_management.src.layer_data_management.neo4j_manager.GraphDatabase.driver")
def test_check_arxiv_node_database_connection_failure(mock_driver, neo4j_db):
    mock_driver.side_effect = ServiceUnavailable("Failed to connect")
    with pytest.raises(ServiceUnavailable):
        neo4j_db.check_arxiv_node_exists()


@patch("services.layer_data_management.src.layer_data_management.neo4j_manager.logger")
@patch("services.layer_data_management.src.layer_data_management.neo4j_manager.GraphDatabase.driver")
def test_create_arxiv_datasource_node_success(mock_driver, mock_logger, neo4j_db):
    neo4j_db.check_arxiv_node_exists = MagicMock(return_value={})
    mock_driver.return_value.__enter__.return_value.execute_query.return_value = (
        [MagicMock(data=lambda: ARXIV_NODE_RESPONSE)],
        MagicMock(counters=MagicMock(nodes_created=1)),
        None,
    )
    result = neo4j_db.create_arxiv_datasource_node(ARXIV_URL)
    assert result == ARXIV_NODE_RESPONSE


@patch("services.layer_data_management.src.layer_data_management.neo4j_manager.logger")
@patch("services.layer_data_management.src.layer_data_management.neo4j_manager.GraphDatabase.driver")
def test_create_arxiv_datasource_node_already_exists(mock_driver, mock_logger, neo4j_db):
    neo4j_db.check_arxiv_node_exists = MagicMock(return_value=ARXIV_NODE_RESPONSE)
    result = neo4j_db.create_arxiv_datasource_node(ARXIV_URL)
    mock_logger.warn.assert_called_once()
    assert result == ARXIV_NODE_RESPONSE


@patch("services.layer_data_management.src.layer_data_management.neo4j_manager.logger")
def test_create_arxiv_datasource_node_missing_params(mock_logger, neo4j_db):
    with pytest.raises(ValueError):
        neo4j_db.create_arxiv_datasource_node(None)
    mock_logger.error.assert_called_once()


@patch("services.layer_data_management.src.layer_data_management.neo4j_manager.logger")
def test_create_arxiv_datasource_node_wrong_param_type(mock_logger, neo4j_db):
    with pytest.raises(ValueError):
        neo4j_db.create_arxiv_datasource_node(1)
    mock_logger.error.assert_called_once()


@patch("services.layer_data_management.src.layer_data_management.neo4j_manager.logger")
def test_create_arxiv_datasource_node_with_missing_params(mock_logger):
    tests = [
        (None, "arXiv base URL is required and must be a string."),
        (1, "arXiv base URL is required and must be a string."),
    ]
    for url, expected in tests:
        with pytest.raises(ValueError):
            Neo4jDatabase(URI, USERNAME, PASSWORD).create_arxiv_datasource_node(url)
        mock_logger.error.assert_called_once()
        mock_logger.reset_mock()


@patch("services.layer_data_management.src.layer_data_management.neo4j_manager.logger")
def test_create_arxiv_datasource_node_with_wrong_param_type(mock_logger):
    with pytest.raises(ValueError):
        Neo4jDatabase(URI, USERNAME, PASSWORD).create_arxiv_datasource_node(1)
    mock_logger.error.assert_called_once()


@patch("services.layer_data_management.src.layer_data_management.neo4j_manager.logger")
def test_create_arxiv_datasource_missing_neo4j_fields(mock_logger, neo4j_db):
    neo4j_db.check_arxiv_node_exists = MagicMock(return_value={})
    with pytest.raises(ValueError):
        neo4j_db.uri = None
        neo4j_db.create_arxiv_datasource_node(ARXIV_URL)
    mock_logger.error.assert_called_once()
    mock_logger.reset_mock()
    with pytest.raises(ValueError):
        neo4j_db.uri = URI
        neo4j_db.username = None
        neo4j_db.create_arxiv_datasource_node(ARXIV_URL)
    mock_logger.error.assert_called_once()
    mock_logger.reset_mock()
    with pytest.raises(ValueError):
        neo4j_db.username = USERNAME
        neo4j_db.password = None
        neo4j_db.create_arxiv_datasource_node(ARXIV_URL)
    mock_logger.error.assert_called_once()


@patch("services.layer_data_management.src.layer_data_management.neo4j_manager.GraphDatabase.driver")
def test_create_arxiv_datasource_node_failed(mock_driver, neo4j_db):
    neo4j_db.check_arxiv_node_exists = MagicMock(return_value={})
    mock_driver.return_value.__enter__.return_value.execute_query.return_value = (
        [MagicMock(data=lambda: ARXIV_NODE_RESPONSE)],
        MagicMock(counters=MagicMock(nodes_created=0)),
        None,
    )
    with pytest.raises(RuntimeError):
        neo4j_db.create_arxiv_datasource_node(ARXIV_URL)
    mock_driver.return_value.__enter__.return_value.execute_query.return_value = (
        [MagicMock(data=lambda: ARXIV_NODE_RESPONSE)],
        MagicMock(counters=MagicMock(nodes_created=2)),
        None,
    )
    with pytest.raises(RuntimeError):
        neo4j_db.create_arxiv_datasource_node(ARXIV_URL)


@patch("services.layer_data_management.src.layer_data_management.neo4j_manager.GraphDatabase.driver")
def test_create_arxiv_raw_data_node_success(mock_driver, neo4j_db):
    arxiv_node = MagicMock()
    neo4j_db.check_arxiv_node_exists = MagicMock(return_value=ARXIV_NODE_RESPONSE)
    arxiv_node.data = MagicMock(return_value=ARXIV_RAW_DATA_RESPONSE)
    mock_driver.return_value.__enter__.return_value.execute_query.return_value = (
        [MagicMock(data=lambda: ARXIV_RAW_DATA_RESPONSE)],
        MagicMock(counters=MagicMock(nodes_created=2, relationships_created=4)),
        None,
    )
    result = neo4j_db.create_arxiv_raw_data_node(
        ARXIV_RAW_DATA_PARAMS["date_from"],
        ARXIV_RAW_DATA_PARAMS["date_to"],
        ARXIV_RAW_DATA_PARAMS["date_obtained"],
        ARXIV_RAW_DATA_PARAMS["method_name"],
        ARXIV_RAW_DATA_PARAMS["method_version"],
        ARXIV_RAW_DATA_PARAMS["size_bytes"],
        ARXIV_RAW_DATA_PARAMS["bucket_name"],
        ARXIV_RAW_DATA_PARAMS["storage_uri"],
    )

    assert result[0].data() == ARXIV_RAW_DATA_RESPONSE


def test_create_arxiv_raw_data_node_dates_missing_or_wrong_type(neo4j_db):
    with pytest.raises(ValueError):
        neo4j_db.create_arxiv_raw_data_node(
            None,
            ARXIV_RAW_DATA_PARAMS["date_to"],
            ARXIV_RAW_DATA_PARAMS["date_obtained"],
            ARXIV_RAW_DATA_PARAMS["method_name"],
            ARXIV_RAW_DATA_PARAMS["method_version"],
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            ARXIV_RAW_DATA_PARAMS["bucket_name"],
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )
    with pytest.raises(ValueError):
        neo4j_db.create_arxiv_raw_data_node(
            123,
            ARXIV_RAW_DATA_PARAMS["date_to"],
            ARXIV_RAW_DATA_PARAMS["date_obtained"],
            ARXIV_RAW_DATA_PARAMS["method_name"],
            ARXIV_RAW_DATA_PARAMS["method_version"],
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            ARXIV_RAW_DATA_PARAMS["bucket_name"],
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )
    with pytest.raises(ValueError):
        neo4j_db.create_arxiv_raw_data_node(
            ARXIV_RAW_DATA_PARAMS["date_from"],
            None,
            ARXIV_RAW_DATA_PARAMS["date_obtained"],
            ARXIV_RAW_DATA_PARAMS["method_name"],
            ARXIV_RAW_DATA_PARAMS["method_version"],
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            ARXIV_RAW_DATA_PARAMS["bucket_name"],
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )
    with pytest.raises(ValueError):
        neo4j_db.create_arxiv_raw_data_node(
            ARXIV_RAW_DATA_PARAMS["date_from"],
            123,
            ARXIV_RAW_DATA_PARAMS["date_obtained"],
            ARXIV_RAW_DATA_PARAMS["method_name"],
            ARXIV_RAW_DATA_PARAMS["method_version"],
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            ARXIV_RAW_DATA_PARAMS["bucket_name"],
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )
    with pytest.raises(ValueError):
        neo4j_db.create_arxiv_raw_data_node(
            ARXIV_RAW_DATA_PARAMS["date_from"],
            ARXIV_RAW_DATA_PARAMS["date_to"],
            None,
            ARXIV_RAW_DATA_PARAMS["method_name"],
            ARXIV_RAW_DATA_PARAMS["method_version"],
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            ARXIV_RAW_DATA_PARAMS["bucket_name"],
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )
    with pytest.raises(ValueError):
        neo4j_db.create_arxiv_raw_data_node(
            ARXIV_RAW_DATA_PARAMS["date_from"],
            ARXIV_RAW_DATA_PARAMS["date_to"],
            123,
            ARXIV_RAW_DATA_PARAMS["method_name"],
            ARXIV_RAW_DATA_PARAMS["method_version"],
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            ARXIV_RAW_DATA_PARAMS["bucket_name"],
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )
    


def test_create_arxiv_raw_data_node_method_name_version_missing_or_wrong_type(neo4j_db):
    with pytest.raises(ValueError):
        neo4j_db.create_arxiv_raw_data_node(
            ARXIV_RAW_DATA_PARAMS["date_from"],
            ARXIV_RAW_DATA_PARAMS["date_to"],
            ARXIV_RAW_DATA_PARAMS["date_obtained"],
            None,
            ARXIV_RAW_DATA_PARAMS["method_version"],
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            ARXIV_RAW_DATA_PARAMS["bucket_name"],
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )
    with pytest.raises(ValueError):
        neo4j_db.create_arxiv_raw_data_node(
            ARXIV_RAW_DATA_PARAMS["date_from"],
            ARXIV_RAW_DATA_PARAMS["date_to"],
            ARXIV_RAW_DATA_PARAMS["date_obtained"],
            ARXIV_RAW_DATA_PARAMS["method_name"],
            None,
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            ARXIV_RAW_DATA_PARAMS["bucket_name"],
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )


@patch("services.layer_data_management.src.layer_data_management.neo4j_manager.GraphDatabase.driver")
def test_create_arxiv_raw_data_node_sizebytes_or_storage_missing_or_wrong_type(mock_driver, neo4j_db):
    with pytest.raises(ValueError):
        neo4j_db.create_arxiv_raw_data_node(
            ARXIV_RAW_DATA_PARAMS["date_from"],
            ARXIV_RAW_DATA_PARAMS["date_to"],
            ARXIV_RAW_DATA_PARAMS["date_obtained"],
            ARXIV_RAW_DATA_PARAMS["method_name"],
            ARXIV_RAW_DATA_PARAMS["method_version"],
            None,
            ARXIV_RAW_DATA_PARAMS["bucket_name"],
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )
    with pytest.raises(ValueError):
        neo4j_db.create_arxiv_raw_data_node(
            ARXIV_RAW_DATA_PARAMS["date_from"],
            ARXIV_RAW_DATA_PARAMS["date_to"],
            ARXIV_RAW_DATA_PARAMS["date_obtained"],
            ARXIV_RAW_DATA_PARAMS["method_name"],
            ARXIV_RAW_DATA_PARAMS["method_version"],
            "1",
            ARXIV_RAW_DATA_PARAMS["bucket_name"],
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )
    with pytest.raises(ValueError):
        neo4j_db.create_arxiv_raw_data_node(
            ARXIV_RAW_DATA_PARAMS["date_from"],
            ARXIV_RAW_DATA_PARAMS["date_to"],
            ARXIV_RAW_DATA_PARAMS["date_obtained"],
            ARXIV_RAW_DATA_PARAMS["method_name"],
            ARXIV_RAW_DATA_PARAMS["method_version"],
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            None,
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )
    with pytest.raises(ValueError):
        neo4j_db.create_arxiv_raw_data_node(
            ARXIV_RAW_DATA_PARAMS["date_from"],
            ARXIV_RAW_DATA_PARAMS["date_to"],
            ARXIV_RAW_DATA_PARAMS["date_obtained"],
            ARXIV_RAW_DATA_PARAMS["method_name"],
            ARXIV_RAW_DATA_PARAMS["method_version"],
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            1,
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )
    with pytest.raises(ValueError):
        neo4j_db.create_arxiv_raw_data_node(
            ARXIV_RAW_DATA_PARAMS["date_from"],
            ARXIV_RAW_DATA_PARAMS["date_to"],
            ARXIV_RAW_DATA_PARAMS["date_obtained"],
            ARXIV_RAW_DATA_PARAMS["method_name"],
            ARXIV_RAW_DATA_PARAMS["method_version"],
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            ARXIV_RAW_DATA_PARAMS["bucket_name"],
            None,
        )
    with pytest.raises(ValueError):
        neo4j_db.create_arxiv_raw_data_node(
            ARXIV_RAW_DATA_PARAMS["date_from"],
            ARXIV_RAW_DATA_PARAMS["date_to"],
            ARXIV_RAW_DATA_PARAMS["date_obtained"],
            ARXIV_RAW_DATA_PARAMS["method_name"],
            ARXIV_RAW_DATA_PARAMS["method_version"],
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            ARXIV_RAW_DATA_PARAMS["bucket_name"],
            1,
        )


@patch("services.layer_data_management.src.layer_data_management.neo4j_manager.GraphDatabase.driver")
def test_create_arxiv_raw_data_node_arxiv_node_not_found(mock_driver, neo4j_db):
    neo4j_db.check_arxiv_node_exists = MagicMock(return_value={})
    with pytest.raises(ValueError):
        neo4j_db.create_arxiv_raw_data_node(
            ARXIV_RAW_DATA_PARAMS["date_from"],
            ARXIV_RAW_DATA_PARAMS["date_to"],
            ARXIV_RAW_DATA_PARAMS["date_obtained"],
            ARXIV_RAW_DATA_PARAMS["method_name"],
            ARXIV_RAW_DATA_PARAMS["method_version"],
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            ARXIV_RAW_DATA_PARAMS["bucket_name"],
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )


@patch("services.layer_data_management.src.layer_data_management.neo4j_manager.GraphDatabase.driver")
def test_create_arxiv_raw_data_node_failed(mock_driver, neo4j_db):
    neo4j_db.check_arxiv_node_exists = MagicMock(return_value=ARXIV_NODE_RESPONSE)
    mock_driver.return_value.__enter__.return_value.execute_query.return_value = (
        [MagicMock(data=lambda: ARXIV_RAW_DATA_RESPONSE)],
        MagicMock(counters=MagicMock(nodes_created=0, relationships_created=0)),
        None,
    )
    with pytest.raises(RuntimeError):
        neo4j_db.create_arxiv_raw_data_node(
            ARXIV_RAW_DATA_PARAMS["date_from"],
            ARXIV_RAW_DATA_PARAMS["date_to"],
            ARXIV_RAW_DATA_PARAMS["date_obtained"],
            ARXIV_RAW_DATA_PARAMS["method_name"],
            ARXIV_RAW_DATA_PARAMS["method_version"],
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            ARXIV_RAW_DATA_PARAMS["bucket_name"],
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )
    mock_driver.return_value.__enter__.return_value.execute_query.return_value = (
        [MagicMock(data=lambda: ARXIV_RAW_DATA_RESPONSE)],
        MagicMock(counters=MagicMock(nodes_created=1, relationships_created=0)),
        None,
    )
    with pytest.raises(RuntimeError):
        neo4j_db.create_arxiv_raw_data_node(
            ARXIV_RAW_DATA_PARAMS["date_from"],
            ARXIV_RAW_DATA_PARAMS["date_to"],
            ARXIV_RAW_DATA_PARAMS["date_obtained"],
            ARXIV_RAW_DATA_PARAMS["method_name"],
            ARXIV_RAW_DATA_PARAMS["method_version"],
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            ARXIV_RAW_DATA_PARAMS["bucket_name"],
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )


def test_create_raw_data_node_neo4j_fields_missing(neo4j_db):
    with pytest.raises(ValueError):
        neo4j_db.uri = None
        neo4j_db.create_arxiv_raw_data_node(
            ARXIV_RAW_DATA_PARAMS["date_from"],
            ARXIV_RAW_DATA_PARAMS["date_to"],
            ARXIV_RAW_DATA_PARAMS["date_obtained"],
            ARXIV_RAW_DATA_PARAMS["method_name"],
            ARXIV_RAW_DATA_PARAMS["method_version"],
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            ARXIV_RAW_DATA_PARAMS["bucket_name"],
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )
    with pytest.raises(ValueError):
        neo4j_db.uri = URI
        neo4j_db.username = None
        neo4j_db.create_arxiv_raw_data_node(
            ARXIV_RAW_DATA_PARAMS["date_from"],
            ARXIV_RAW_DATA_PARAMS["date_to"],
            ARXIV_RAW_DATA_PARAMS["date_obtained"],
            ARXIV_RAW_DATA_PARAMS["method_name"],
            ARXIV_RAW_DATA_PARAMS["method_version"],
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            ARXIV_RAW_DATA_PARAMS["bucket_name"],
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )
    with pytest.raises(ValueError):
        neo4j_db.username = USERNAME
        neo4j_db.password = None
        neo4j_db.create_arxiv_raw_data_node(
            ARXIV_RAW_DATA_PARAMS["date_from"],
            ARXIV_RAW_DATA_PARAMS["date_to"],
            ARXIV_RAW_DATA_PARAMS["date_obtained"],
            ARXIV_RAW_DATA_PARAMS["method_name"],
            ARXIV_RAW_DATA_PARAMS["method_version"],
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            ARXIV_RAW_DATA_PARAMS["bucket_name"],
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )


@patch("services.layer_data_management.src.layer_data_management.neo4j_manager.GraphDatabase.driver")
def test_create_arxiv_parsed_node_success(mock_driver, neo4j_db):
    arxiv_node = MagicMock()
    neo4j_db.check_arxiv_node_exists = MagicMock(return_value=ARXIV_NODE_RESPONSE)
    arxiv_node.data = MagicMock(return_value=ARXIV_RAW_DATA_RESPONSE)
    mock_driver.return_value.__enter__.return_value.execute_query.return_value = (
        [MagicMock(data=lambda: ARXIV_RAW_DATA_RESPONSE)],
        MagicMock(counters=MagicMock(nodes_created=2, relationships_created=6)),
        None,
    )
    result = neo4j_db.create_arxiv_parsed_node(
        ARXIV_RAW_DATA_PARAMS["storage_uri"],
        ARXIV_RAW_DATA_PARAMS["size_bytes"],
        ARXIV_RAW_DATA_PARAMS["method_name"],
        ARXIV_RAW_DATA_PARAMS["method_version"],
        datetime.now(),
        ARXIV_RAW_DATA_PARAMS["bucket_name"],
        ARXIV_RAW_DATA_PARAMS["storage_uri"],
    )

    assert result[0].data() == ARXIV_RAW_DATA_RESPONSE


def test_create_arxiv_parsed_node_missing_or_wrong_type(neo4j_db):
    with pytest.raises(ValueError):
        neo4j_db.create_arxiv_parsed_node(
            123,
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            ARXIV_RAW_DATA_PARAMS["method_name"],
            ARXIV_RAW_DATA_PARAMS["method_version"],
            datetime.now(),
            ARXIV_RAW_DATA_PARAMS["bucket_name"],
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )
    with pytest.raises(ValueError):
        neo4j_db.create_arxiv_parsed_node(
            None,
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            ARXIV_RAW_DATA_PARAMS["method_name"],
            ARXIV_RAW_DATA_PARAMS["method_version"],
            datetime.now(),
            ARXIV_RAW_DATA_PARAMS["bucket_name"],
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )
    with pytest.raises(ValueError):
        neo4j_db.create_arxiv_parsed_node(
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
            "123",
            ARXIV_RAW_DATA_PARAMS["method_name"],
            ARXIV_RAW_DATA_PARAMS["method_version"],
            datetime.now(),
            ARXIV_RAW_DATA_PARAMS["bucket_name"],
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )
    with pytest.raises(ValueError):
        neo4j_db.create_arxiv_parsed_node(
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
            None,
            ARXIV_RAW_DATA_PARAMS["method_name"],
            ARXIV_RAW_DATA_PARAMS["method_version"],
            datetime.now(),
            ARXIV_RAW_DATA_PARAMS["bucket_name"],
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )
    with pytest.raises(ValueError):
        neo4j_db.create_arxiv_parsed_node(
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            123,
            ARXIV_RAW_DATA_PARAMS["method_version"],
            datetime.now(),
            ARXIV_RAW_DATA_PARAMS["bucket_name"],
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )
    with pytest.raises(ValueError):
        neo4j_db.create_arxiv_parsed_node(
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            None,
            ARXIV_RAW_DATA_PARAMS["method_version"],
            datetime.now(),
            ARXIV_RAW_DATA_PARAMS["bucket_name"],
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )
    with pytest.raises(ValueError):
        neo4j_db.create_arxiv_parsed_node(
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            ARXIV_RAW_DATA_PARAMS["method_name"],
            123,
            datetime.now(),
            ARXIV_RAW_DATA_PARAMS["bucket_name"],
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )
    with pytest.raises(ValueError):
        neo4j_db.create_arxiv_parsed_node(
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            ARXIV_RAW_DATA_PARAMS["method_name"],
            None,
            datetime.now(),
            ARXIV_RAW_DATA_PARAMS["bucket_name"],
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )
    with pytest.raises(ValueError):
        neo4j_db.create_arxiv_parsed_node(
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            ARXIV_RAW_DATA_PARAMS["method_name"],
            ARXIV_RAW_DATA_PARAMS["method_version"],
            123,
            ARXIV_RAW_DATA_PARAMS["bucket_name"],
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )
    with pytest.raises(ValueError):
        neo4j_db.create_arxiv_parsed_node(
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            ARXIV_RAW_DATA_PARAMS["method_name"],
            ARXIV_RAW_DATA_PARAMS["method_version"],
            None,
            ARXIV_RAW_DATA_PARAMS["bucket_name"],
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )
    with pytest.raises(ValueError):
        neo4j_db.create_arxiv_parsed_node(
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            ARXIV_RAW_DATA_PARAMS["method_name"],
            ARXIV_RAW_DATA_PARAMS["method_version"],
            datetime.now(),
            123,
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )
    with pytest.raises(ValueError):
        neo4j_db.create_arxiv_parsed_node(
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            ARXIV_RAW_DATA_PARAMS["method_name"],
            ARXIV_RAW_DATA_PARAMS["method_version"],
            datetime.now(),
            None,
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )
    with pytest.raises(ValueError):
        neo4j_db.create_arxiv_parsed_node(
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            ARXIV_RAW_DATA_PARAMS["method_name"],
            ARXIV_RAW_DATA_PARAMS["method_version"],
            datetime.now(),
            ARXIV_RAW_DATA_PARAMS["bucket_name"],
            123,
        )
    with pytest.raises(ValueError):
        neo4j_db.create_arxiv_parsed_node(
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            ARXIV_RAW_DATA_PARAMS["method_name"],
            ARXIV_RAW_DATA_PARAMS["method_version"],
            datetime.now(),
            ARXIV_RAW_DATA_PARAMS["bucket_name"],
            None,
        )

def test_check_arxiv_research_exists_with_missing_params(neo4j_db):
    with pytest.raises(ValueError):
        neo4j_db.check_arxiv_research_exists(None)
    with pytest.raises(ValueError):
        neo4j_db.check_arxiv_research_exists(1)

def test_check_arxiv_research_exists_with_valid_identifier(neo4j_db):
    with patch("services.layer_data_management.src.layer_data_management.neo4j_manager.GraphDatabase.driver") as mock_driver:
        mock_session = MagicMock()
        mock_driver.return_value.__enter__.return_value = mock_session
        mock_session.execute_query.return_value = ([MagicMock(data=lambda: {"arxivId": "1234.5678"})], None, None)

        result = neo4j_db.check_arxiv_research_exists("1234.5678")
        assert result == {"arxivId": "1234.5678"}

def test_check_arxiv_research_exists_with_non_existent_identifier(neo4j_db):
    with patch("services.layer_data_management.src.layer_data_management.neo4j_manager.GraphDatabase.driver") as mock_driver:
        mock_session = MagicMock()
        mock_driver.return_value.__enter__.return_value = mock_session
        mock_session.execute_query.return_value = ([], None, None)

        result = neo4j_db.check_arxiv_research_exists("non_existent_id")
        assert result == {}

def test_check_arxiv_research_exists_with_multiple_records(neo4j_db):
    with patch("services.layer_data_management.src.layer_data_management.neo4j_manager.GraphDatabase.driver") as mock_driver:
        mock_session = MagicMock()
        mock_driver.return_value.__enter__.return_value = mock_session
        mock_session.execute_query.return_value = ([MagicMock(), MagicMock()], None, None)

        with pytest.raises(RuntimeError):
            neo4j_db.check_arxiv_research_exists("duplicate_id")

def test_check_arxiv_research_exists_with_database_error(neo4j_db):
    with patch("services.layer_data_management.src.layer_data_management.neo4j_manager.GraphDatabase.driver") as mock_driver:
        mock_driver.side_effect = Exception("Database connection error")

        with pytest.raises(Exception):
            neo4j_db.check_arxiv_research_exists("1234.5678")

@patch('services.layer_data_management.src.layer_data_management.neo4j_manager.GraphDatabase.driver')
def test_create_arxiv_parsed_node_success(mock_driver, neo4j_db):
    mock_driver.return_value.verify_connectivity.return_value = None
    mock_driver.return_value.__enter__.return_value.execute_query.return_value = mock_driver.return_value.execute_query.return_value = (
        ARXIV_RAW_DATA_RESPONSE,
        MagicMock(counters=MagicMock(nodes_created=2, relationships_created=0)),
        None,
    )
    
    result = neo4j_db.create_arxiv_parsed_node(
        raw_data_key="raw_key", 
        size_bytes=100,
        service_name="parser",
        service_version="1.0",
        parsed_date=datetime(2023, 3, 28),
        raw_data_bucket_name="raw-bucket",
        output_key="output_key"
    )
    assert isinstance(result, dict)
    assert result == ARXIV_RAW_DATA_RESPONSE

def test_create_arxiv_parsed_node_missing_credentials(neo4j_db):
    neo4j_db.username = None
    with pytest.raises(ValueError):
        neo4j_db.create_arxiv_parsed_node(
            raw_data_key="raw_key",
            size_bytes=100, 
            service_name="parser",
            service_version="1.0",
            parsed_date=datetime(2023, 3, 28),
            raw_data_bucket_name="raw-bucket",
            output_key="output_key"
        )
    neo4j_db.username = "neo4j"
    neo4j_db.password = None
    with pytest.raises(ValueError):
        neo4j_db.create_arxiv_parsed_node(
            raw_data_key="raw_key",
            size_bytes=100, 
            service_name="parser",
            service_version="1.0",
            parsed_date=datetime(2023, 3, 28),
            raw_data_bucket_name="raw-bucket",
            output_key="output_key"
        )

def test_create_arxiv_parsed_node_missing_required_params(neo4j_db):
    with pytest.raises(ValueError):
        neo4j_db.create_arxiv_parsed_node(
            raw_data_key=None,
            size_bytes=100,
            service_name="parser", 
            service_version="1.0",
            parsed_date=datetime(2023, 3, 28),
            raw_data_bucket_name="raw-bucket",
            output_key="output_key"
        )

def test_create_arxiv_parsed_node_invalid_param_types(neo4j_db):
    with pytest.raises(ValueError):
        neo4j_db.create_arxiv_parsed_node(
            raw_data_key=123, 
            size_bytes="100",
            service_name="parser",
            service_version="1.0", 
            parsed_date="2023-03-28",
            raw_data_bucket_name="raw-bucket",
            output_key="output_key"  
        )
    
@patch('services.layer_data_management.src.layer_data_management.neo4j_manager.GraphDatabase.driver')
def test_create_arxiv_parsed_node_incorrect_nodes_created(mock_driver, neo4j_db):
    mock_driver.return_value.verify_connectivity.return_value = None  
    mock_driver.return_value.__enter__.return_value.execute_query.return_value = (
        [MagicMock(data=lambda: ARXIV_RAW_DATA_RESPONSE)],
        MagicMock(counters=MagicMock(nodes_created=0, relationships_created=0)),
        None,
    )

    with pytest.raises(RuntimeError):
        neo4j_db.create_arxiv_parsed_node(
            raw_data_key="raw_key",
            size_bytes=100,
            service_name="parser",
            service_version="1.0",
            parsed_date=datetime(2023, 3, 28), 
            raw_data_bucket_name="raw-bucket",
            output_key="output_key"
        )