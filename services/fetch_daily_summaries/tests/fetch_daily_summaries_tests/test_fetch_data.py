import pytest
import requests
from unittest.mock import patch, Mock, call
from requests.exceptions import HTTPError

from services.fetch_daily_summaries.src.fetch_daily_summaries import fetch_data


class TestFetchData:
    valid_response = '''<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/ http://www.openarchives.org/OAI/2.0/OAI-PMH.xsd">
<responseDate>2024-01-27T17:53:42Z</responseDate>
<request verb="ListRecords" from="2024-01-25" metadataPrefix="oai_dc" set="cs">http://export.arxiv.org/oai2</request>
<ListRecords>
<record>
<!-- record data -->
</record>
<resumptionToken cursor="0" completeListSize="1162">6960524|1001</resumptionToken>
</ListRecords>
</OAI-PMH>'''
    @patch('services.fetch_daily_summaries.src.fetch_daily_summaries.requests.get')
    @patch('services.fetch_daily_summaries.src.fetch_daily_summaries.time.sleep')
    def test_fetch_data(self, mock_sleep, mock_get):
        base_url = "http://example.com"
        from_date = "2024-01-01"
        set_param = "test_set"

        first_response_content = self.valid_response
        second_response_content = '<OAI-PMH><ListRecords></ListRecords></OAI-PMH>'

        first_response = requests.Response()
        first_response.status_code = 200
        first_response._content = bytes(first_response_content, 'utf-8')

        second_response = requests.Response()
        second_response.status_code = 200
        second_response._content = bytes(second_response_content, 'utf-8')

        mock_get.side_effect = [first_response, second_response]

        xml_responses = fetch_data(base_url, from_date, set_param)

        assert len(xml_responses) == 2
        assert xml_responses[0] == first_response_content
        assert xml_responses[1] == second_response_content
        mock_get.assert_called()
        mock_sleep.assert_called()

    @patch('services.fetch_daily_summaries.src.fetch_daily_summaries.requests.get')
    @patch('services.fetch_daily_summaries.src.fetch_daily_summaries.time.sleep')
    def test_fetch_data_handles_http_error(self, mock_sleep, mock_get):
        base_url = "http://example.com"
        from_date = "2024-01-01"
        set_param = "test_set"

        error_response = requests.Response()
        error_response.status_code = 500
        error_response._content = bytes("Internal Server Error", 'utf-8')

        mock_get.return_value = error_response

        xml_responses = fetch_data(base_url, from_date, set_param)

        assert len(xml_responses) == 0

    @patch('services.fetch_daily_summaries.src.fetch_daily_summaries.requests.get')
    @patch('services.fetch_daily_summaries.src.fetch_daily_summaries.time.sleep')
    def test_fetch_data_retries_twice_on_503(self, mock_sleep, mock_get):
        base_url = "http://example.com"
        from_date = "2024-01-01"
        set_param = "test_set"

        error_response_503 = requests.Response()
        error_response_503.status_code = 503
        error_response_503._content = bytes("Service Unavailable", 'utf-8')

        mock_get.side_effect = [error_response_503] * 3

        xml_responses = fetch_data(base_url, from_date, set_param)

        assert len(xml_responses) == 0
        assert mock_get.call_count == 3
        assert mock_sleep.call_count == 2
        assert mock_sleep.call_args_list == [call(30), call(120)]