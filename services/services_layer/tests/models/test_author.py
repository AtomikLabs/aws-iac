from unittest.mock import MagicMock, patch

import pytest
from neo4j import Driver

from services.services_layer.src.services_layer.models.author import Author


class TestAuthor:

    TEXT = "This is a test author"
    STORAGE_URL = "s3://test-bucket/test-key"
    URL = "https://arxiv.org/abs/1906.11285"
    DATE = "2019-06-26"
    UUID = "1234-5678-9012-3456"
    CREATED = "2021-01-01T00:00:00"
    LAST_MODIFIED = "2021-01-01T00:00:00"

    SINGLE_CREATE_RECORDS_RETURN = MagicMock(
        data=lambda: {
            "a": {
                "text": TestAuthor.TEXT,
                "storage_url": TestAuthor.STORAGE_URL,
                "url": TestAuthor.URL,
                "uuid": TestAuthor.UUID,
                "created": TestAuthor.CREATED,
                "last_modified": TestAuthor.LAST_MODIFIED,
            }
        }
    )

    @pytest.fixture
    def _created(self):
        return TestAuthor.CREATED

    @pytest.fixture
    def driver(self):
        driver = MagicMock(spec=Driver)
        driver.verify_connectivity = MagicMock()
        return driver

    @pytest.fixture
    def _last_modified(self):
        return TestAuthor.LAST_MODIFIED

    @pytest.fixture
    def _storage_url(self):
        return TestAuthor.STORAGE_URL

    @pytest.fixture
    def _text(self):
        return TestAuthor.TEXT

    @pytest.fixture
    def _url(self):
        return TestAuthor.URL

    @pytest.fixture
    def _uuid(self):
        return TestAuthor.UUID

    def test_init_should_succeed_with_valid_params(self, driver, _url, _text, _storage_url):
        author = Author(driver, _url, _text, _storage_url)
        assert author.driver == driver
        assert author.url == _url
        assert author.text == _text
        assert author.storage_url == _storage_url
        assert author.uuid is None
        assert author.created is None
        assert author.last_modified is None

    @pytest.mark.parametrize(
        "d, u, t, s",
        [
            (None, "https://arxiv.org/abs/1906.11285", "This is a test author", "s3://test-bucket/test-key"),
            (123, "https://arxiv.org/abs/1906.11285", "This is a test author", "s3://test-bucket/test-key"),
            (MagicMock(spec=Driver), 123, "This is a test author", "s3://test-bucket/test-key"),
            (MagicMock(spec=Driver), "https://arxiv.org/abs/1906.11285", 123, "s3://test-bucket/test-key"),
            (MagicMock(spec=Driver), "https://arxiv.org/abs/1906.11285", "This is a test author", 123),
        ],
    )
    def test_init_should_raise_exception_with_invalid_params(self, d, u, t, s):
        with pytest.raises(ValueError):
            Author(d, u, t, s)

    @patch("services.services_layer.src.services_layer.models.author.uuid")
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
        author = Author(driver, _url, _text, _storage_url)
        author.create()
        driver.execute_query.assert_called_once()
        assert author.url == _url
        assert author.text == _text
        assert author.storage_url == _storage_url
        assert author.uuid == _uuid
        assert author.created == _created
        assert author.last_modified == _last_modified

    @pytest.mark.parametrize(
        "d, u, t, s",
        [
            (None, "https://arxiv.org/abs/1906.11285", "This is a test author", "s3://test-bucket/test-key"),
            (123, "https://arxiv.org/abs/1906.11285", "This is a test author", "s3://test-bucket/test-key"),
            (MagicMock(spec=Driver), 123, "This is a test author", "s3://test-bucket/test-key"),
            (MagicMock(spec=Driver), "https://arxiv.org/abs/1906.11285", 123, "s3://test-bucket/test-key"),
            (MagicMock(spec=Driver), "https://arxiv.org/abs/1906.11285", "This is a test author", 123),
        ],
    )
    def test_create_should_raise_exception_with_invalid_params(self, d, u, t, s, driver, _url):
        author = Author(driver, _url)
        author.url = u
        author.text = t
        author.storage_url = s
        if not isinstance(d, Driver):
            with pytest.raises(AttributeError):
                author.driver = d
                author.create()
        else:
            with pytest.raises(ValueError):
                author.create()

    def test_create_should_raise_exception_when_no_records_returned(self, driver, _url, _text, _storage_url):
        driver.execute_query.return_value = ([], MagicMock(counters=MagicMock(nodes_created=0)), [])
        author = Author(driver, _url, _text, _storage_url)
        with pytest.raises(RuntimeError):
            author.create()
        driver.execute_query.assert_called_once()

    def test_create_should_not_duplicate_Author(self, driver, _url, _text, _storage_url):
        driver.execute_query.return_value = (
            [self.SINGLE_CREATE_RECORDS_RETURN],
            MagicMock(counters=MagicMock(nodes_created=0)),
            ["a"],
        )
        text = "A Møøse once bit my sister... No realli!"
        author = Author(driver, _url, _text, _storage_url)
        author.text = text
        author.create()
        driver.execute_query.assert_called_once()
        assert author.text == _text

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
        author = Author(driver, _url, _text, _storage_url)
        with pytest.raises(ValueError):
            author.create()
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
                            "created": "",
                            "last_modified": _last_modified,
                        }
                    }
                )
            ],
            MagicMock(counters=MagicMock(nodes_created=1)),
            ["a"],
        )
        with pytest.raises(ValueError):
            author.create()
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
                            "last_modified": "",
                        }
                    }
                )
            ],
            MagicMock(counters=MagicMock(nodes_created=1)),
            ["a"],
        )
        with pytest.raises(ValueError):
            author.create()
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
        author = Author(driver, _url)
        assert author.load()
        assert "MATCH (a:Author {url: $url}) RETURN a" in driver.execute_query.call_args[0]
        assert author.url == _url
        assert author.text == _text
        assert author.storage_url == _storage_url
        assert author.uuid == _uuid
        assert author.created == _created
        assert author.last_modified == _last_modified

    def test_load_should_return_false_if_record_does_not_exist(self, driver, _url):
        driver.execute_query.return_value = ([], MagicMock(counters=MagicMock(nodes_created=0)), [])
        author = Author(driver, _url)
        assert not author.load()
        assert "MATCH (a:Author {url: $url}) RETURN a" in driver.execute_query.call_args[0]
        assert author.url == _url
        assert author.text == ""
        assert author.storage_url == ""
        assert author.uuid is None
        assert author.created is None
        assert author.last_modified is None

    def test_load_should_raise_exception_if_invalid_url(self, driver, _url):
        author = Author(driver, _url)
        author.url = None
        with pytest.raises(ValueError):
            author.load()
        author.url = 123
        with pytest.raises(ValueError):
            author.load()

    def test_load_should_raise_exception_if_driver_not_connected(self, driver, _url):
        driver.verify_connectivity.side_effect = Exception("Connection error")
        author = Author(driver, _url)
        with pytest.raises(Exception):
            author.load()
        driver.verify_connectivity.assert_called_once()

    @pytest.mark.parametrize(
        "query",
        [
            (
                MagicMock(
                    data=lambda: {
                        "a": {
                            "url": "",
                            "text": "This is a test author",
                            "storage_url": "s3://test-bucket/test-key",
                            "uuid": "1234-5678-9012-3456",
                            "created": "2021-01-01T00:00:00",
                            "last_modified": "2021-01-01T00:00:00",
                        }
                    }
                )
            ),
            (
                MagicMock(
                    data=lambda: {
                        "a": {
                            "url": "",
                            "text": "This is a test author",
                            "storage_url": "s3://test-bucket/test-key",
                            "uuid": "1234-5678-9012-3456",
                            "created": "2021-01-01T00:00:00",
                            "last_modified": "2021-01-01T00:00:00",
                        }
                    }
                )
            ),
            (
                MagicMock(
                    data=lambda: {
                        "a": {
                            "url": "",
                            "text": "This is a test author",
                            "storage_url": "s3://test-bucket/test-key",
                            "uuid": "1234-5678-9012-3456",
                            "created": "2021-01-01T00:00:00",
                            "last_modified": "2021-01-01T00:00:00",
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
        author = Author(driver, _url)
        with pytest.raises(ValueError):
            author.load()
        driver.execute_query.assert_called_once()
        driver.reset_mock()

    def test_find_should_return_author(self, driver, _url, _text, _storage_url, _uuid, _created, _last_modified):
        driver.execute_query.return_value = (
            [self.SINGLE_CREATE_RECORDS_RETURN],
            MagicMock(counters=MagicMock(nodes_created=1)),
            ["a"],
        )
        author = Author.find(driver, _url)
        driver.execute_query.assert_called_once()
        assert author.url == _url
        assert author.text == _text
        assert author.storage_url == _storage_url
        assert author.uuid == _uuid
        assert author.created == _created
        assert author.last_modified == _last_modified

    def test_find_should_return_none_if_no_record(self, driver, _url):
        driver.execute_query.return_value = (
            [MagicMock(data=lambda: {})],
            MagicMock(counters=MagicMock(nodes_created=0)),
            [],
        )
        author = Author.find(driver, _url)
        driver.execute_query.assert_called_once()
        assert author is None

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
            Author.find(d, u)

    def test_find_should_raise_exception_if_driver_not_connected(self, driver, _url):
        driver.verify_connectivity.side_effect = Exception("Connection error")
        with pytest.raises(Exception):
            Author.find(driver, _url)
        driver.verify_connectivity.assert_called_once()

    def test_find_all_should_should_turn_all_found_records(
        self, driver, _url, _text, _storage_url, _uuid, _created, _last_modified
    ):
        driver.execute_query.return_value = (
            [self.SINGLE_CREATE_RECORDS_RETURN, self.SINGLE_CREATE_RECORDS_RETURN],
            MagicMock(counters=MagicMock()),
            ["a", "a"],
        )
        authors = Author.find_all(driver)
        driver.execute_query.assert_called_once()
        assert len(authors) == 2
        for author in authors:
            assert author.url == _url
            assert author.text == _text
            assert author.storage_url == _storage_url
            assert author.uuid == _uuid
            assert author.created == _created
            assert author.last_modified == _last_modified
