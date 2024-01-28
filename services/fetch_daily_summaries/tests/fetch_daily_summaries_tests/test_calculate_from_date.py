from datetime import datetime
from services.fetch_daily_summaries.src.fetch_daily_summaries import calculate_from_date


class TestCalculateFromDate:

    def test_calculate_from_date_returns_expected_date(self):
        result = calculate_from_date()
        assert result == datetime.today().date()
