from unittest.mock import patch, call
from services.fetch_daily_summaries.src.fetch_daily_summaries import log_initial_info


class TestLogInitialInfo:
    @patch('services.fetch_daily_summaries.src.fetch_daily_summaries.logger.info')
    def test_log_initial_info_logs_correct_info(self, mock_info):
        event = {'key': 'value'}
        log_initial_info(event)
        calls = [call(f"Received event: {event}"), call("Starting to fetch arXiv daily summaries")]
        mock_info.assert_has_calls(calls, any_order=False)