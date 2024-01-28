from datetime import date, timedelta
from unittest.mock import patch

import pytest

from services.fetch_daily_summaries.src.fetch_daily_summaries import Database, get_earliest_unfetched_date


class TestGetEarliestUnfetchedDate:
    MOCKED_TODAY = date(2024, 1, 27)
    MOCK_DB = Database("test_aurora_cluster_arn", "test_db_credentials_secret_arn", "test_database")

    @patch.object(Database, "execute_sql")
    @patch("datetime.date")
    def test_get_earliest_unfetched_date(self, mock_date, mock_execute_sql):
        mocked_today = self.MOCKED_TODAY
        expected_earliest_date = mocked_today - timedelta(days=6)
        mock_date.today.return_value = mocked_today
        mock_execute_sql.return_value = {"records": []}

        earliest_date = get_earliest_unfetched_date(
            self.MOCKED_TODAY,
            self.MOCK_DB,
        )

        assert earliest_date is not None
        assert earliest_date == expected_earliest_date

    def test_get_earliest_unfetched_dated_raises_error_when_today_is_none(self):
        with pytest.raises(ValueError):
            get_earliest_unfetched_date(None, self.MOCK_DB)

    def test_get_earliest_unfetched_date_returns_none_when_sql_query_returns_no_rows(self):
        result = get_earliest_unfetched_date(self.MOCKED_TODAY, self.MOCK_DB)
        assert result is None

    def test_get_earliest_unfetched_date_raises_error_when_days_is_negative(self):
        with pytest.raises(ValueError):
            get_earliest_unfetched_date(self.MOCKED_TODAY, self.MOCK_DB, days=-1)

    def test_get_earliest_unfetched_date_raises_error_when_days_is_zero(self):
        with pytest.raises(ValueError):
            get_earliest_unfetched_date(self.MOCKED_TODAY, self.MOCK_DB, 0)

    def test_get_earliest_unfetched_date_raises_error_when_days_is_greater_than_10(self):
        with pytest.raises(ValueError):
            get_earliest_unfetched_date(self.MOCKED_TODAY, self.MOCK_DB, 32)

    def test_get_earliest_unfetched_date_raises_error_when_days_is_not_an_integer(self):
        with pytest.raises(ValueError):
            get_earliest_unfetched_date(self.MOCKED_TODAY, self.MOCK_DB, "invalid_days")
