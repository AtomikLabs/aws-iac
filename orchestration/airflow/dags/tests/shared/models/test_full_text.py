from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from neo4j import Driver

from services.services_layer.src.services_layer.constants import S3_KEY_DATE_FORMAT
from services.services_layer.src.services_layer.models.full_text import FullText


class TestFullText:

    TEXT = "This is a test full_text"
    STORAGE_URL = "s3://test-bucket/test-key"
    URL = "https://arxiv.org/abs/1906.11285"
    DATE = "2019-06-26"
    UUID = "1234-5678-9012-3456"
    CREATED = datetime.strptime("2021-01-01T00-00-00", S3_KEY_DATE_FORMAT)
    LAST_MODIFIED = datetime.strptime("2021-01-01T00-00-00", S3_KEY_DATE_FORMAT)

    SINGLE_CREATE_RECORDS_RETURN = MagicMock(
        data=lambda: {
            "a": {
                "text": TestFullText.TEXT,
                "storage_url": TestFullText.STORAGE_URL,
                "url": TestFullText.URL,
                "uuid": TestFullText.UUID,
                "created": TestFullText.CREATED,
                "last_modified": TestFullText.LAST_MODIFIED,
            }
        }
    )

    @pytest.fixture
    def _created(self):
        return TestFullText.CREATED

    @pytest.fixture
    def driver(self):
        driver = MagicMock(spec=Driver)
        driver.verify_connectivity = MagicMock()
        return driver

    @pytest.fixture
    def _last_modified(self):
        return TestFullText.LAST_MODIFIED

    @pytest.fixture
    def _storage_url(self):
        return TestFullText.STORAGE_URL

    @pytest.fixture
    def _text(self):
        return TestFullText.TEXT

    @pytest.fixture
    def _url(self):
        return TestFullText.URL

    @pytest.fixture
    def _uuid(self):
        return TestFullText.UUID

    def test_init_should_succeed_with_valid_params(self, driver, _url, _text, _storage_url):
        full_text = FullText(driver, _url, _text, _storage_url)
        assert full_text.driver == driver
        assert full_text.url == _url
        assert full_text.text == _text
        assert full_text.storage_url == _storage_url
        assert full_text.uuid is None
        assert full_text.created is None
        assert full_text.last_modified is None

    @pytest.mark.parametrize(
        "d, u, t, s",
        [
            (None, "https://arxiv.org/abs/1906.11285", "This is a test full_text", "s3://test-bucket/test-key"),
            (123, "https://arxiv.org/abs/1906.11285", "This is a test full_text", "s3://test-bucket/test-key"),
            (MagicMock(spec=Driver), 123, "This is a test full_text", "s3://test-bucket/test-key"),
            (MagicMock(spec=Driver), "https://arxiv.org/abs/1906.11285", 123, "s3://test-bucket/test-key"),
            (MagicMock(spec=Driver), "https://arxiv.org/abs/1906.11285", "This is a test full_text", 123),
        ],
    )
    def test_init_should_raise_exception_with_invalid_params(self, d, u, t, s):
        with pytest.raises(ValueError):
            FullText(d, u, t, s)

    @patch("services.services_layer.src.services_layer.models.full_text.uuid")
    def test_create_should_succeed_with_valid_params(
        self,
        mock_uuid,
        driver,
        _url,
        _text,
        _storage_url,
        _uuid,
        _created,
        _last_modified,
    ):
        mock_uuid.uuid4 = MagicMock(return_value=_uuid)
        driver.execute_query.return_value = (
            [
                MagicMock(
                    data=lambda: {
                        "a": {
                            "url": _url,
                            "text": _text,
                            "storage_url": _storage_url,
                            "uuid": _uuid,
                            "created": _created,
                            "last_modified": _last_modified,
                        }
                    }
                )
            ],
            MagicMock(counters=MagicMock(nodes_created=1)),
            ["a"],
        )
        full_text = FullText(driver, _url, _text, _storage_url)
        full_text.create()
        driver.execute_query.assert_called_once()
        assert full_text.url == _url
        assert full_text.text == _text
        assert full_text.storage_url == _storage_url
        assert full_text.uuid == _uuid
        assert full_text.created == _created
        assert full_text.last_modified == _last_modified

    @pytest.mark.parametrize(
        "d, u, t, s",
        [
            (None, "https://arxiv.org/abs/1906.11285", "This is a test full_text", "s3://test-bucket/test-key"),
            (123, "https://arxiv.org/abs/1906.11285", "This is a test full_text", "s3://test-bucket/test-key"),
            (MagicMock(spec=Driver), 123, "This is a test full_text", "s3://test-bucket/test-key"),
            (MagicMock(spec=Driver), "https://arxiv.org/abs/1906.11285", 123, "s3://test-bucket/test-key"),
            (MagicMock(spec=Driver), "https://arxiv.org/abs/1906.11285", "This is a test full_text", 123),
        ],
    )
    def test_create_should_raise_exception_with_invalid_params(self, d, u, t, s, driver, _url):
        full_text = FullText(driver, _url)
        full_text.url = u
        full_text.text = t
        full_text.storage_url = s
        if not isinstance(d, Driver):
            with pytest.raises(AttributeError):
                full_text.driver = d
                full_text.create()
        else:
            with pytest.raises(ValueError):
                full_text.create()

    def test_create_should_raise_exception_when_no_records_returned(self, driver, _url, _text, _storage_url):
        driver.execute_query.return_value = ([], MagicMock(counters=MagicMock(nodes_created=0)), [])
        full_text = FullText(driver, _url, _text, _storage_url)
        with pytest.raises(RuntimeError):
            full_text.create()
        driver.execute_query.assert_called_once()

    def test_create_should_not_duplicate_FullText(self, driver, _url, _text, _storage_url):
        driver.execute_query.return_value = (
            [self.SINGLE_CREATE_RECORDS_RETURN],
            MagicMock(counters=MagicMock(nodes_created=0)),
            ["a"],
        )
        text = "A Møøse once bit my sister... No realli!"
        full_text = FullText(driver, _url, _text, _storage_url)
        full_text.text = text
        full_text.create()
        driver.execute_query.assert_called_once()
        assert full_text.text == _text

    def test_create_should_raise_exception_if_record_improperly_created(
        self, driver, _url, _text, _storage_url, _uuid, _created, _last_modified
    ):
        driver.execute_query.return_value = (
            [
                MagicMock(
                    data=lambda: {
                        "a": {
                            "url": _url,
                            "text": _text,
                            "storage_url": _storage_url,
                            "uuid": "",
                            "created": _created,
                            "last_modified": _last_modified,
                        }
                    }
                )
            ],
            MagicMock(counters=MagicMock(nodes_created=1)),
            ["a"],
        )
        full_text = FullText(driver, _url, _text, _storage_url)
        with pytest.raises(ValueError):
            full_text.create()
        driver.execute_query.assert_called_once()
        driver.reset_mock()
        driver.execute_query.return_value = (
            [
                MagicMock(
                    data=lambda: {
                        "a": {
                            "url": _url,
                            "text": _text,
                            "storage_url": _storage_url,
                            "uuid": _uuid,
                            "created": None,
                            "last_modified": _last_modified,
                        }
                    }
                )
            ],
            MagicMock(counters=MagicMock(nodes_created=1)),
            ["a"],
        )
        with pytest.raises(ValueError):
            full_text.create()
        driver.execute_query.assert_called_once()
        driver.reset_mock()
        driver.execute_query.return_value = (
            [
                MagicMock(
                    data=lambda: {
                        "a": {
                            "url": _url,
                            "text": _text,
                            "storage_url": _storage_url,
                            "uuid": _uuid,
                            "created": _created,
                            "last_modified": None,
                        }
                    }
                )
            ],
            MagicMock(counters=MagicMock(nodes_created=1)),
            ["a"],
        )
        with pytest.raises(ValueError):
            full_text.create()
        driver.execute_query.assert_called_once()

    def test_load_should_succeed_if_record_exists(
        self,
        driver,
        _url,
        _text,
        _storage_url,
        _uuid,
        _created,
        _last_modified,
    ):
        driver.execute_query.return_value = (
            [self.SINGLE_CREATE_RECORDS_RETURN],
            MagicMock(counters=MagicMock(nodes_created=1)),
            ["a"],
        )
        full_text = FullText(driver, _url)
        assert full_text.load()
        assert "MATCH (a:FullText {url: $url}) RETURN a" in driver.execute_query.call_args[0]
        assert full_text.url == _url
        assert full_text.text == _text
        assert full_text.storage_url == _storage_url
        assert full_text.uuid == _uuid
        assert full_text.created == _created
        assert full_text.last_modified == _last_modified

    def test_load_should_return_false_if_record_does_not_exist(self, driver, _url):
        driver.execute_query.return_value = ([], MagicMock(counters=MagicMock(nodes_created=0)), [])
        full_text = FullText(driver, _url)
        assert not full_text.load()
        assert "MATCH (a:FullText {url: $url}) RETURN a" in driver.execute_query.call_args[0]
        assert full_text.url == _url
        assert full_text.text == ""
        assert full_text.storage_url == ""
        assert full_text.uuid is None
        assert full_text.created is None
        assert full_text.last_modified is None

    def test_load_should_raise_exception_if_invalid_url(self, driver, _url):
        full_text = FullText(driver, _url)
        full_text.url = None
        with pytest.raises(ValueError):
            full_text.load()
        full_text.url = 123
        with pytest.raises(ValueError):
            full_text.load()

    def test_load_should_raise_exception_if_driver_not_connected(self, driver, _url):
        driver.verify_connectivity.side_effect = Exception("Connection error")
        full_text = FullText(driver, _url)
        with pytest.raises(Exception):
            full_text.load()
        driver.verify_connectivity.assert_called_once()

    @pytest.mark.parametrize(
        "query",
        [
            (
                MagicMock(
                    data=lambda: {
                        "a": {
                            "url": "",
                            "text": "This is a test full_text",
                            "storage_url": "s3://test-bucket/test-key",
                            "uuid": "1234-5678-9012-3456",
                            "created": datetime.strptime("2021-01-01T00-00-00", S3_KEY_DATE_FORMAT),
                            "last_modified": datetime.strptime("2021-01-01T00-00-00", S3_KEY_DATE_FORMAT),
                        }
                    }
                )
            ),
            (
                MagicMock(
                    data=lambda: {
                        "a": {
                            "url": "",
                            "text": "This is a test full_text",
                            "storage_url": "s3://test-bucket/test-key",
                            "uuid": "1234-5678-9012-3456",
                            "created": datetime.strptime("2021-01-01T00-00-00", S3_KEY_DATE_FORMAT),
                            "last_modified": datetime.strptime("2021-01-01T00-00-00", S3_KEY_DATE_FORMAT),
                        }
                    }
                )
            ),
            (
                MagicMock(
                    data=lambda: {
                        "a": {
                            "url": "",
                            "text": "This is a test full_text",
                            "storage_url": "s3://test-bucket/test-key",
                            "uuid": "1234-5678-9012-3456",
                            "created": datetime.strptime("2021-01-01T00-00-00", S3_KEY_DATE_FORMAT),
                            "last_modified": datetime.strptime("2021-01-01T00-00-00", S3_KEY_DATE_FORMAT),
                        }
                    }
                )
            ),
        ],
    )
    def test_load_should_raise_exception_if_returned_values_not_valid(self, query, driver, _url):
        driver.execute_query.return_value = (
            [query],
            MagicMock(counters=MagicMock(nodes_created=1)),
            ["a"],
        )
        full_text = FullText(driver, _url)
        with pytest.raises(ValueError):
            full_text.load()
        driver.execute_query.assert_called_once()
        driver.reset_mock()

    def test_find_should_return_full_text(self, driver, _url, _text, _storage_url, _uuid, _created, _last_modified):
        driver.execute_query.return_value = (
            [self.SINGLE_CREATE_RECORDS_RETURN],
            MagicMock(counters=MagicMock(nodes_created=1)),
            ["a"],
        )
        full_text = FullText.find(driver, _url)
        driver.execute_query.assert_called_once()
        assert full_text.url == _url
        assert full_text.text == _text
        assert full_text.storage_url == _storage_url
        assert full_text.uuid == _uuid
        assert full_text.created == _created
        assert full_text.last_modified == _last_modified

    def test_find_should_return_none_if_no_record(self, driver, _url):
        driver.execute_query.return_value = (
            [MagicMock(data=lambda: {})],
            MagicMock(counters=MagicMock(nodes_created=0)),
            [],
        )
        full_text = FullText.find(driver, _url)
        driver.execute_query.assert_called_once()
        assert full_text is None

    @pytest.mark.parametrize(
        "d, u",
        [
            (None, "https://arxiv.org/abs/1906.11285"),
            (123, "https://arxiv.org/abs/1906.11285"),
            (MagicMock(spec=Driver), 123),
        ],
    )
    def test_find_should_raise_exception_if_invalid_params(self, d, u):
        with pytest.raises(ValueError):
            FullText.find(d, u)

    def test_find_should_raise_exception_if_driver_not_connected(self, driver, _url):
        driver.verify_connectivity.side_effect = Exception("Connection error")
        with pytest.raises(Exception):
            FullText.find(driver, _url)
        driver.verify_connectivity.assert_called_once()

    def test_find_all_should_should_turn_all_found_records(
        self, driver, _url, _text, _storage_url, _uuid, _created, _last_modified
    ):
        driver.execute_query.return_value = (
            [self.SINGLE_CREATE_RECORDS_RETURN, self.SINGLE_CREATE_RECORDS_RETURN],
            MagicMock(counters=MagicMock()),
            ["a", "a"],
        )
        full_texts = FullText.find_all(driver)
        driver.execute_query.assert_called_once()
        assert len(full_texts) == 2
        for full_text in full_texts:
            assert full_text.url == _url
            assert full_text.text == _text
            assert full_text.storage_url == _storage_url
            assert full_text.uuid == _uuid
            assert full_text.created == _created
            assert full_text.last_modified == _last_modified
