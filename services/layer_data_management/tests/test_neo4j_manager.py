from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest
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
    error_message = "URI, username, and password are required but one or more are not set."
    with pytest.raises(ValueError) as exc_info:
        db = Neo4jDatabase(URI, USERNAME, PASSWORD)
        db.uri = None
        db.check_arxiv_node_exists()
    assert error_message in str(exc_info.value)
    with pytest.raises(ValueError) as exc_info:
        db.uri = URI
        db.username = None
        db.check_arxiv_node_exists()
    assert error_message in str(exc_info.value)
    with pytest.raises(ValueError) as exc_info:
        db.username = USERNAME
        db.password = None
        db.check_arxiv_node_exists()
    assert error_message in str(exc_info.value)


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
    with pytest.raises(ValueError) as exc_info:
        neo4j_db.check_arxiv_node_exists()
    assert "Multiple arXiv DataSource nodes found" in str(exc_info.value)


@patch("services.layer_data_management.src.layer_data_management.neo4j_manager.GraphDatabase.driver")
def test_check_arxiv_node_database_connection_failure(mock_driver, neo4j_db):
    mock_driver.side_effect = ServiceUnavailable("Failed to connect")
    with pytest.raises(ServiceUnavailable) as exc_info:
        neo4j_db.check_arxiv_node_exists()
    assert "Failed to connect" in str(exc_info.value)


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
    with pytest.raises(ValueError) as exc_info:
        neo4j_db.create_arxiv_datasource_node(None)
    assert "arXiv base URL is required and must be a string." in str(exc_info.value)
    mock_logger.error.assert_called_once()


@patch("services.layer_data_management.src.layer_data_management.neo4j_manager.logger")
def test_create_arxiv_datasource_node_wrong_param_type(mock_logger, neo4j_db):
    with pytest.raises(ValueError) as exc_info:
        neo4j_db.create_arxiv_datasource_node(1)
    assert "arXiv base URL is required and must be a string." in str(exc_info.value)
    mock_logger.error.assert_called_once()


@patch("services.layer_data_management.src.layer_data_management.neo4j_manager.logger")
def test_create_arxiv_datasource_node_with_missing_params(mock_logger):
    tests = [
        (None, "arXiv base URL is required and must be a string."),
        (1, "arXiv base URL is required and must be a string."),
    ]
    for url, expected in tests:
        with pytest.raises(ValueError) as exc_info:
            Neo4jDatabase(URI, USERNAME, PASSWORD).create_arxiv_datasource_node(url)
        assert expected in str(exc_info.value)
        mock_logger.error.assert_called_once()
        mock_logger.reset_mock()


@patch("services.layer_data_management.src.layer_data_management.neo4j_manager.logger")
def test_create_arxiv_datasource_node_with_wrong_param_type(mock_logger):
    with pytest.raises(ValueError) as exc_info:
        Neo4jDatabase(URI, USERNAME, PASSWORD).create_arxiv_datasource_node(1)
    assert "arXiv base URL is required and must be a string." in str(exc_info.value)
    mock_logger.error.assert_called_once()


@patch("services.layer_data_management.src.layer_data_management.neo4j_manager.logger")
def test_create_arxiv_datasource_missing_neo4j_fields(mock_logger, neo4j_db):
    message = "URI, username, and password are required but one or more are not set."
    neo4j_db.check_arxiv_node_exists = MagicMock(return_value={})
    with pytest.raises(ValueError) as exc_info:
        neo4j_db.uri = None
        neo4j_db.create_arxiv_datasource_node(ARXIV_URL)
    assert message in str(exc_info.value)
    mock_logger.error.assert_called_once()
    mock_logger.reset_mock()
    with pytest.raises(ValueError) as exc_info:
        neo4j_db.uri = URI
        neo4j_db.username = None
        neo4j_db.create_arxiv_datasource_node(ARXIV_URL)
    assert message in str(exc_info.value)
    mock_logger.error.assert_called_once()
    mock_logger.reset_mock()
    with pytest.raises(ValueError) as exc_info:
        neo4j_db.username = USERNAME
        neo4j_db.password = None
        neo4j_db.create_arxiv_datasource_node(ARXIV_URL)
    assert message in str(exc_info.value)
    mock_logger.error.assert_called_once()


@patch("services.layer_data_management.src.layer_data_management.neo4j_manager.GraphDatabase.driver")
def test_create_arxiv_datasource_node_failed(mock_driver, neo4j_db):
    neo4j_db.check_arxiv_node_exists = MagicMock(return_value={})
    mock_driver.return_value.__enter__.return_value.execute_query.return_value = (
        [MagicMock(data=lambda: ARXIV_NODE_RESPONSE)],
        MagicMock(counters=MagicMock(nodes_created=0)),
        None,
    )
    message = "Failed to create arXiv DataSource node or multiple nodes were created."
    with pytest.raises(RuntimeError) as exc_info:
        neo4j_db.create_arxiv_datasource_node(ARXIV_URL)
    assert message in str(exc_info.value)
    mock_driver.return_value.__enter__.return_value.execute_query.return_value = (
        [MagicMock(data=lambda: ARXIV_NODE_RESPONSE)],
        MagicMock(counters=MagicMock(nodes_created=2)),
        None,
    )
    message = "Failed to create arXiv DataSource node or multiple nodes were created."
    with pytest.raises(RuntimeError) as exc_info:
        neo4j_db.create_arxiv_datasource_node(ARXIV_URL)
    assert message in str(exc_info.value)


@patch("services.layer_data_management.src.layer_data_management.neo4j_manager.GraphDatabase.driver")
def test_create_arxiv_raw_data_node_success(mock_driver, neo4j_db):
    arxiv_node = MagicMock()
    neo4j_db.check_arxiv_node_exists = MagicMock(return_value=ARXIV_NODE_RESPONSE)
    arxiv_node.data = MagicMock(return_value=ARXIV_RAW_DATA_RESPONSE)
    mock_driver.return_value.__enter__.return_value.execute_query.return_value = (
        [MagicMock(data=lambda: ARXIV_RAW_DATA_RESPONSE)],
        MagicMock(counters=MagicMock(nodes_created=2, relationships_created=6)),
        None,
    )
    result = neo4j_db.create_arxiv_raw_data_node(
        ARXIV_RAW_DATA_PARAMS["date_from"],
        ARXIV_RAW_DATA_PARAMS["date_to"],
        ARXIV_RAW_DATA_PARAMS["date_obtained"],
        ARXIV_RAW_DATA_PARAMS["method_name"],
        ARXIV_RAW_DATA_PARAMS["method_version"],
        ARXIV_RAW_DATA_PARAMS["size_bytes"],
        ARXIV_RAW_DATA_PARAMS["storage_uri"],
    )

    assert result[0].data() == ARXIV_RAW_DATA_RESPONSE


def test_create_arxiv_raw_data_node_dates_missing_or_wrong_type(neo4j_db):
    message = "Date from, date to, and date obtained are required and must be dates."
    with pytest.raises(ValueError) as exc_info:
        neo4j_db.create_arxiv_raw_data_node(
            None,
            ARXIV_RAW_DATA_PARAMS["date_to"],
            ARXIV_RAW_DATA_PARAMS["date_obtained"],
            ARXIV_RAW_DATA_PARAMS["method_name"],
            ARXIV_RAW_DATA_PARAMS["method_version"],
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )
    assert message in str(exc_info.value)
    with pytest.raises(ValueError) as exc_info:
        neo4j_db.create_arxiv_raw_data_node(
            ARXIV_RAW_DATA_PARAMS["date_from"],
            None,
            ARXIV_RAW_DATA_PARAMS["date_obtained"],
            ARXIV_RAW_DATA_PARAMS["method_name"],
            ARXIV_RAW_DATA_PARAMS["method_version"],
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )
    assert message in str(exc_info.value)
    with pytest.raises(ValueError) as exc_info:
        neo4j_db.create_arxiv_raw_data_node(
            ARXIV_RAW_DATA_PARAMS["date_from"],
            ARXIV_RAW_DATA_PARAMS["date_to"],
            None,
            ARXIV_RAW_DATA_PARAMS["method_name"],
            ARXIV_RAW_DATA_PARAMS["method_version"],
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )


def test_create_arxiv_raw_data_node_method_name_version_missing_or_wrong_type(neo4j_db):
    message = "Method name and method version are required and must be strings."
    with pytest.raises(ValueError) as exc_info:
        neo4j_db.create_arxiv_raw_data_node(
            ARXIV_RAW_DATA_PARAMS["date_from"],
            ARXIV_RAW_DATA_PARAMS["date_to"],
            ARXIV_RAW_DATA_PARAMS["date_obtained"],
            None,
            ARXIV_RAW_DATA_PARAMS["method_version"],
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )
    assert message in str(exc_info.value)
    with pytest.raises(ValueError) as exc_info:
        neo4j_db.create_arxiv_raw_data_node(
            ARXIV_RAW_DATA_PARAMS["date_from"],
            ARXIV_RAW_DATA_PARAMS["date_to"],
            ARXIV_RAW_DATA_PARAMS["date_obtained"],
            ARXIV_RAW_DATA_PARAMS["method_name"],
            None,
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )
    assert message in str(exc_info.value)


@patch("services.layer_data_management.src.layer_data_management.neo4j_manager.GraphDatabase.driver")
def test_create_arxiv_raw_data_node_sizebytes_or_storage_missing_or_wrong_type(mock_driver, neo4j_db):
    message = message = "Size and storage URI are required and must be integers and strings, respectively."
    with pytest.raises(ValueError) as exc_info:
        neo4j_db.create_arxiv_raw_data_node(
            ARXIV_RAW_DATA_PARAMS["date_from"],
            ARXIV_RAW_DATA_PARAMS["date_to"],
            ARXIV_RAW_DATA_PARAMS["date_obtained"],
            ARXIV_RAW_DATA_PARAMS["method_name"],
            ARXIV_RAW_DATA_PARAMS["method_version"],
            None,
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )
    assert message in str(exc_info.value)
    with pytest.raises(ValueError) as exc_info:
        neo4j_db.create_arxiv_raw_data_node(
            ARXIV_RAW_DATA_PARAMS["date_from"],
            ARXIV_RAW_DATA_PARAMS["date_to"],
            ARXIV_RAW_DATA_PARAMS["date_obtained"],
            ARXIV_RAW_DATA_PARAMS["method_name"],
            ARXIV_RAW_DATA_PARAMS["method_version"],
            "1",
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )
    assert message in str(exc_info.value)
    with pytest.raises(ValueError) as exc_info:
        neo4j_db.create_arxiv_raw_data_node(
            ARXIV_RAW_DATA_PARAMS["date_from"],
            ARXIV_RAW_DATA_PARAMS["date_to"],
            ARXIV_RAW_DATA_PARAMS["date_obtained"],
            ARXIV_RAW_DATA_PARAMS["method_name"],
            ARXIV_RAW_DATA_PARAMS["method_version"],
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            None,
        )
    assert message in str(exc_info.value)
    with pytest.raises(ValueError) as exc_info:
        neo4j_db.create_arxiv_raw_data_node(
            ARXIV_RAW_DATA_PARAMS["date_from"],
            ARXIV_RAW_DATA_PARAMS["date_to"],
            ARXIV_RAW_DATA_PARAMS["date_obtained"],
            ARXIV_RAW_DATA_PARAMS["method_name"],
            ARXIV_RAW_DATA_PARAMS["method_version"],
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            1,
        )
    assert message in str(exc_info.value)


@patch("services.layer_data_management.src.layer_data_management.neo4j_manager.GraphDatabase.driver")
def test_create_arxiv_raw_data_node_arxiv_node_not_found(mock_driver, neo4j_db):
    neo4j_db.check_arxiv_node_exists = MagicMock(return_value={})
    with pytest.raises(ValueError) as exc_info:
        neo4j_db.create_arxiv_raw_data_node(
            ARXIV_RAW_DATA_PARAMS["date_from"],
            ARXIV_RAW_DATA_PARAMS["date_to"],
            ARXIV_RAW_DATA_PARAMS["date_obtained"],
            ARXIV_RAW_DATA_PARAMS["method_name"],
            ARXIV_RAW_DATA_PARAMS["method_version"],
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )
    assert "arXiv DataSource node does not exist. Must create it first." in str(exc_info.value)


@patch("services.layer_data_management.src.layer_data_management.neo4j_manager.GraphDatabase.driver")
def test_create_arxiv_raw_data_node_failed(mock_driver, neo4j_db):
    neo4j_db.check_arxiv_node_exists = MagicMock(return_value=ARXIV_NODE_RESPONSE)
    mock_driver.return_value.__enter__.return_value.execute_query.return_value = (
        [MagicMock(data=lambda: ARXIV_RAW_DATA_RESPONSE)],
        MagicMock(counters=MagicMock(nodes_created=0, relationships_created=0)),
        None,
    )
    message = "Failed to create arXiv raw data node or multiple nodes were created."
    with pytest.raises(RuntimeError) as exc_info:
        neo4j_db.create_arxiv_raw_data_node(
            ARXIV_RAW_DATA_PARAMS["date_from"],
            ARXIV_RAW_DATA_PARAMS["date_to"],
            ARXIV_RAW_DATA_PARAMS["date_obtained"],
            ARXIV_RAW_DATA_PARAMS["method_name"],
            ARXIV_RAW_DATA_PARAMS["method_version"],
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )
    assert message in str(exc_info.value)
    mock_driver.return_value.__enter__.return_value.execute_query.return_value = (
        [MagicMock(data=lambda: ARXIV_RAW_DATA_RESPONSE)],
        MagicMock(counters=MagicMock(nodes_created=1, relationships_created=0)),
        None,
    )
    with pytest.raises(RuntimeError) as exc_info:
        neo4j_db.create_arxiv_raw_data_node(
            ARXIV_RAW_DATA_PARAMS["date_from"],
            ARXIV_RAW_DATA_PARAMS["date_to"],
            ARXIV_RAW_DATA_PARAMS["date_obtained"],
            ARXIV_RAW_DATA_PARAMS["method_name"],
            ARXIV_RAW_DATA_PARAMS["method_version"],
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )
    assert message in str(exc_info.value)


def test_create_raw_data_node_neo4j_fields_missing(neo4j_db):
    message = "URI, username, and password are required but one or more are not set."
    with pytest.raises(ValueError) as exc_info:
        neo4j_db.uri = None
        neo4j_db.create_arxiv_raw_data_node(
            ARXIV_RAW_DATA_PARAMS["date_from"],
            ARXIV_RAW_DATA_PARAMS["date_to"],
            ARXIV_RAW_DATA_PARAMS["date_obtained"],
            ARXIV_RAW_DATA_PARAMS["method_name"],
            ARXIV_RAW_DATA_PARAMS["method_version"],
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )
    assert message in str(exc_info.value)
    with pytest.raises(ValueError) as exc_info:
        neo4j_db.uri = URI
        neo4j_db.username = None
        neo4j_db.create_arxiv_raw_data_node(
            ARXIV_RAW_DATA_PARAMS["date_from"],
            ARXIV_RAW_DATA_PARAMS["date_to"],
            ARXIV_RAW_DATA_PARAMS["date_obtained"],
            ARXIV_RAW_DATA_PARAMS["method_name"],
            ARXIV_RAW_DATA_PARAMS["method_version"],
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )
    assert message in str(exc_info.value)
    with pytest.raises(ValueError) as exc_info:
        neo4j_db.username = USERNAME
        neo4j_db.password = None
        neo4j_db.create_arxiv_raw_data_node(
            ARXIV_RAW_DATA_PARAMS["date_from"],
            ARXIV_RAW_DATA_PARAMS["date_to"],
            ARXIV_RAW_DATA_PARAMS["date_obtained"],
            ARXIV_RAW_DATA_PARAMS["method_name"],
            ARXIV_RAW_DATA_PARAMS["method_version"],
            ARXIV_RAW_DATA_PARAMS["size_bytes"],
            ARXIV_RAW_DATA_PARAMS["storage_uri"],
        )
