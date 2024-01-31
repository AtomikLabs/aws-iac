from unittest.mock import patch

from services.parse_arxiv_summaries.src.parse_arxiv_summaries import log_initial_info


class TestLogInitialInfo:
    @patch("services.parse_arxiv_summaries.src.parse_arxiv_summaries.logger.info")
    def test_log_initial_info_logs_correct_info(self, mock_info):
        event = {"key": "value"}
        log_initial_info(event)
        mock_info.assert_any_call("## EVENT")
        mock_info.assert_any_call(event)
