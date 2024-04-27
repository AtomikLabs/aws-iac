from datetime import datetime
from unittest.mock import patch

import pytz
from dags.shared.utils import DEFAULT_TIMEZONE, get_storage_key_date, get_storage_key_datetime


@patch("dags.shared.utils.datetime")
def test_get_storage_key_date(mock_datetime):
    expected_date = "2023-03-30T12-00-00"
    mock_datetime.now.return_value = datetime(2023, 3, 30, 12, 0, 0, tzinfo=pytz.timezone(DEFAULT_TIMEZONE))

    result = get_storage_key_date()

    assert result == expected_date
    mock_datetime.now.assert_called_once()


@patch("dags.shared.utils.datetime")
def test_get_storage_key_date_different_timezone(mock_datetime):
    expected_date = "2023-03-29T19-00-00"
    mock_datetime.now.return_value = datetime(2023, 3, 30, 2, 0, 0, tzinfo=pytz.utc)  # UTC time

    result = get_storage_key_date()

    assert result == expected_date
    mock_datetime.now.assert_called_once()


def test_get_storage_key_datetime_without_date_str():
    expected_datetime = datetime.now().astimezone(pytz.timezone(DEFAULT_TIMEZONE))

    with patch("dags.shared.utils.datetime") as mock_datetime:
        mock_datetime.now.return_value = expected_datetime
        result = get_storage_key_datetime()

    assert result == expected_datetime
    mock_datetime.now.assert_called_once()
