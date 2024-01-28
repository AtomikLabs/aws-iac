import pytest
from datetime import date
from unittest.mock import MagicMock

from services.fetch_daily_summaries.src.fetch_daily_summaries import get_fetch_status, Database


class TestGetFetchStatus:
    MOCK_DB = Database('test_aurora_cluster_arn', 'test_db_credentials_secret_arn', 'test_database')

    def test_get_fetch_status_returns_correct_status(self):

        db = MagicMock()
        db.execute_sql.return_value = {
            "records": [
                [{"stringValue": "success"}]
            ]
        }
        result = get_fetch_status(date.today(), db)
        assert result == "success"

    def test_get_fetch_status_raises_error_when_date_is_not_a_date(self):
        with pytest.raises(TypeError):
            get_fetch_status('not a date', self.MOCK_DB)

    def test_get_fetch_status_raises_error_when_date_is_none(self):
        with pytest.raises(TypeError):
            get_fetch_status(None, db=self.MOCK_DB)

    def test_get_fetch_status_raises_error_when_date_is_empty_string(self):
        with pytest.raises(TypeError):
            get_fetch_status('', db=self.MOCK_DB)