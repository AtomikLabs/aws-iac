import pytest
from unittest.mock import patch
from datetime import date
from services.fetch_daily_summaries.src.fetch_daily_summaries import Database, insert_fetch_status


class TestInsertFetchStatus:
    @patch.object(Database, 'execute_sql')
    def test_insert_fetch_status_executes_correct_sql(self, mock_execute_sql):
        test_date = date(2022, 1, 1)
        db = Database('test_aurora_cluster_arn', 'test_db_credentials_secret_arn', 'test_database')

        insert_fetch_status(test_date, db)

        expected_sql_statement = """
    INSERT INTO research_fetch_status (fetch_date, status)
    VALUES (CAST(:date AS DATE), 'pending') ON CONFLICT (fetch_date) DO NOTHING
    """
        expected_parameters = [{"name": "date", "value": {"stringValue": '2022-01-01'}}]

        mock_execute_sql.assert_called_once_with(expected_sql_statement, expected_parameters)

    def test_insert_fetch_status_throws_exception_when_no_date_provided(self):
        db = Database('test_aurora_cluster_arn', 'test_db_credentials_secret_arn', 'test_database')

        with pytest.raises(ValueError):
            insert_fetch_status(None, db)

    def test_insert_fetch_status_throws_exception_when_no_database_provided(self):
        test_date = date(2022, 1, 1)

        with pytest.raises(ValueError):
            insert_fetch_status(test_date, None)
