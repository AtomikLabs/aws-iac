from unittest.mock import MagicMock, patch

import pytest

from services.fetch_daily_summaries.src.fetch_daily_summaries.neo4j_manager import Neo4jDatabase


@pytest.fixture
def mock_graph_database_driver():
    with patch("neo4j.GraphDatabase.driver") as mock:
        yield mock


@pytest.fixture
def valid_neo4j_credentials():
    return {"uri": "neo4j://localhost:7687", "username": "neo4j", "password": "password"}


@pytest.fixture
def neo4j_db(valid_neo4j_credentials):
    return Neo4jDatabase(**valid_neo4j_credentials)


def test_neo4j_database_initialization_failure_missing_params():
    with pytest.raises(ValueError) as exc_info:
        Neo4jDatabase(None, None, None)
    assert "Password, URI, and user are required." in str(exc_info.value)


def test_check_arxiv_node_exists_success(mock_graph_database_driver, neo4j_db):
    mock_session = mock_graph_database_driver.return_value.__enter__.return_value
    mock_session.execute_query.return_value = ([MagicMock(data=lambda: {"uuid": "some_uuid"})], None, None)

    result = neo4j_db.check_arxiv_node_exists()
    assert result == {"uuid": "some_uuid"}


def test_create_arxiv_datasource_node_exists(mock_graph_database_driver, neo4j_db):
    mock_session = mock_graph_database_driver.return_value.__enter__.return_value
    mock_session.execute_query.return_value = ([MagicMock(data=lambda: {"uuid": "some_uuid"})], None, None)

    result = neo4j_db.create_arxiv_datasource_node("http://arxiv.org")
    assert "uuid" in result


# TODO: Add full test suite
