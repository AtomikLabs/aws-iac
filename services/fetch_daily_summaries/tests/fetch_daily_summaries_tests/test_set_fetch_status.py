import pytest
from unittest.mock import MagicMock
from datetime import date
from services.fetch_daily_summaries.src.fetch_daily_summaries import Database, set_fetch_status


class TestSetFetchStatus:
    def test_set_fetch_status_executes_correct_sql(self):
        test_date = date(2022, 1, 1)
        test_status = 'pending'
        db = MagicMock()
        db.execute_sql.return_value = {"records": []}

        set_fetch_status(test_date, test_status, db)

        expected_sql_statement = "UPDATE research_fetch_status SET status = :status \
            WHERE fetch_date = CAST(:date AS DATE)"
        expected_parameters = [
            {"name": "date", "value": {"stringValue": '2022-01-01'}},
            {"name": "status", "value": {"stringValue": 'pending'}}
        ]

        db.execute_sql.assert_called_once_with(expected_sql_statement, expected_parameters)

    def test_set_fetch_status_throws_exception_when_no_date_provided(self):
        db = Database('test_aurora_cluster_arn', 'test_db_credentials_secret_arn', 'test_database')

        with pytest.raises(ValueError):
            set_fetch_status(None, 'pending', db)

    def test_set_fetch_status_throws_exception_when_no_status_provided(self):
        test_date = date(2022, 1, 1)

        with pytest.raises(ValueError):
            set_fetch_status(test_date, None, None)

    def test_set_fetch_status_throws_exception_when_no_database_provided(self):
        test_date = date(2022, 1, 1)
        test_status = 'pending'

        with pytest.raises(ValueError):
            set_fetch_status(test_date, test_status, None)