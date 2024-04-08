from unittest.mock import MagicMock, patch

import pytest
from neo4j import Driver

from services.services_layer.src.services_layer.models.data import Data


class TestData:

    URL = "https://arxiv.org"
    FORMAT = "xml"
    DESCRIPTION = "A description"
    SIZE_BYTES = 123456789
    UUID = "1234-5678-9012-3456"
    CREATED = "2021-01-01T00:00:00"
    LAST_MODIFIED = "2021-01-01T00:00:00"

    SINGLE_CREATE_RECORDS_RETURN = MagicMock(
        data=lambda: {
            "a": {
                "url": TestData.URL,
                "format": TestData.FORMAT,
                "description": TestData.DESCRIPTION,
                "size_bytes": TestData.SIZE_BYTES,
                "uuid": TestData.UUID,
                "created": TestData.CREATED,
                "last_modified": TestData.LAST_MODIFIED,
            }
        }
    )

    @pytest.fixture
    def _url(self):
        return TestData.URL

    @pytest.fixture
    def driver(self):
        driver = MagicMock(spec=Driver)
        driver.verify_connectivity = MagicMock()
        return driver

    @pytest.fixture
    def _format(self):
        return TestData.FORMAT

    @pytest.fixture
    def _description(self):
        return TestData.DESCRIPTION

    @pytest.fixture
    def _size_bytes(self):
        return TestData.SIZE_BYTES

    @pytest.fixture
    def _uuid(self):
        return TestData.UUID

    @pytest.fixture
    def _created(self):
        return TestData.CREATED

    @pytest.fixture
    def _last_modified(self):
        return TestData.LAST_MODIFIED

    def test_init_should_succeed_with_valid_params(self, driver, _url, _format, _description, _size_bytes):
        data = Data(driver, _url, _format, _description, _size_bytes)
        assert data.driver == driver
        assert data.url == _url
        assert data.format == _format
        assert data.description == _description
        assert data.size_bytes == _size_bytes
        assert data.uuid is None
        assert data.created is None
        assert data.last_modified is None

    @pytest.mark.parametrize(
        "d, u, n, desc, s",
        [
            (None, "http://arxiv.org", "format", "desc", 123),
            (123, "http://arxiv.org", "format", "desc", 123),
            (MagicMock(spec=Driver), None, "format", "desc", 123),
            (MagicMock(spec=Driver), 123, "format", "desc", 123),
            (MagicMock(spec=Driver), "http://arxiv.org", None, "desc", 123),
            (MagicMock(spec=Driver), "http://arxiv.org", 123, "desc", 123),
            (MagicMock(spec=Driver), "http://arxiv.org", "format", None, 123),
            (MagicMock(spec=Driver), "http://arxiv.org", "format", 123, 123),
            (MagicMock(spec=Driver), "http://arxiv.org", "format", "desc", None),
            (MagicMock(spec=Driver), "http://arxiv.org", "format", "desc", "123"),
        ],
    )
    def test_init_should_raise_exception_with_invalid_params(self, d, u, n, desc, s):
        with pytest.raises(ValueError):
            Data(d, u, n, desc, s)

    @patch("services.services_layer.src.services_layer.models.data.uuid")
    def test_create_should_succeed_with_valid_params(
        self, mock_uuid, driver, _url, _format, _description, _size_bytes, _uuid
    ):
        mock_uuid.uuid4 = MagicMock(return_value=_uuid)
        driver.execute_query.return_value = (
            [
                MagicMock(
                    data=lambda: {
                        "a": {
                            "url": self.URL,
                            "format": self.FORMAT,
                            "description": self.DESCRIPTION,
                            "size_bytes": self.SIZE_BYTES,
                            "uuid": self.UUID,
                            "created": self.CREATED,
                            "last_modified": self.LAST_MODIFIED,
                        }
                    }
                )
            ],
            MagicMock(counters=MagicMock(nodes_created=1)),
            ["a"],
        )
        data = Data(driver, _url, _format, _description, _size_bytes)
        data.create()
        driver.execute_query.assert_called_once()
        assert data.uuid == self.UUID
        assert data.created
        assert data.last_modified
        print(data.created)

    @pytest.mark.parametrize(
        "d, u, n, desc, s",
        [
            (None, "http://arxiv.org", "format", "desc", 123),
            (123, "http://arxiv.org", "format", "desc", 123),
            (MagicMock(spec=Driver), None, "format", "desc", 123),
            (MagicMock(spec=Driver), 123, "format", "desc", 123),
            (MagicMock(spec=Driver), "http://arxiv.org", None, "desc", 123),
            (MagicMock(spec=Driver), "http://arxiv.org", 123, "desc", 123),
            (MagicMock(spec=Driver), "http://arxiv.org", "format", None, 123),
            (MagicMock(spec=Driver), "http://arxiv.org", "format", 123, 123),
            (MagicMock(spec=Driver), "http://arxiv.org", "format", "desc", None),
            (MagicMock(spec=Driver), "http://arxiv.org", "format", "desc", "123"),
        ],
    )
    def test_create_should_raise_exception_with_invalid_params(
        self, d, u, n, desc, s, driver, _url, _format, _description, _size_bytes
    ):
        data = Data(driver, _url, _format, _description, _size_bytes)
        data.url = u
        data.format = n
        data.description = desc
        data.size_bytes = s
        if not isinstance(d, Driver):
            with pytest.raises(AttributeError):
                data.driver = d
                data.create()
        else:
            with pytest.raises(ValueError):
                data.driver = driver
                data.create()

    def test_create_should_raise_exception_when_no_records_returned(
        self, driver, _url, _format, _description, _size_bytes
    ):
        driver.execute_query.return_value = ([], MagicMock(counters=MagicMock(nodes_created=0)), [])
        data = Data(driver, _url, _format, _description, _size_bytes)
        with pytest.raises(RuntimeError):
            data.create()
        driver.execute_query.assert_called_once()

    def test_create_should_not_duplicate_data(self, driver, _url, _format, _description, _size_bytes):
        driver.execute_query.return_value = (
            [self.SINGLE_CREATE_RECORDS_RETURN],
            MagicMock(counters=MagicMock(nodes_created=0)),
            ["a"],
        )
        format = "C0mput3r Sc13nc3"
        data = Data(driver, _url, format, _description, _size_bytes)
        data.create()
        driver.execute_query.assert_called_once()
        assert data.format == _format

    def test_create_should_raise_exception_if_record_improperly_created(
        self, driver, _url, _format, _description, _size_bytes
    ):
        driver.execute_query.return_value = (
            [
                MagicMock(
                    data=lambda: {
                        "a": {
                            "url": self.URL,
                            "format": self.FORMAT,
                            "description": self.DESCRIPTION,
                            "size_bytes": self.SIZE_BYTES,
                            "uuid": "",
                            "created": self.CREATED,
                            "last_modified": self.LAST_MODIFIED,
                        }
                    }
                )
            ],
            MagicMock(counters=MagicMock(nodes_created=1)),
            ["a"],
        )
        data = Data(driver, _url, _format, _description, _size_bytes)
        with pytest.raises(ValueError):
            data.create()
        driver.execute_query.assert_called_once()
        driver.reset_mock()
        driver.execute_query.return_value = (
            [
                MagicMock(
                    data=lambda: {
                        "a": {
                            "url": self.URL,
                            "format": self.FORMAT,
                            "description": self.DESCRIPTION,
                            "size_bytes": self.SIZE_BYTES,
                            "uuid": self.UUID,
                            "created": "",
                            "last_modified": self.LAST_MODIFIED,
                        }
                    }
                )
            ],
            MagicMock(counters=MagicMock(nodes_created=1)),
            ["a"],
        )
        with pytest.raises(ValueError):
            data.create()
        driver.execute_query.assert_called_once()
        driver.reset_mock()
        driver.execute_query.return_value = (
            [
                MagicMock(
                    data=lambda: {
                        "a": {
                            "url": self.URL,
                            "format": self.FORMAT,
                            "description": self.DESCRIPTION,
                            "size_bytes": self.SIZE_BYTES,
                            "uuid": self.UUID,
                            "created": self.CREATED,
                            "last_modified": "",
                        }
                    }
                )
            ],
            MagicMock(counters=MagicMock(nodes_created=1)),
            ["a"],
        )
        with pytest.raises(ValueError):
            data.create()
        driver.execute_query.assert_called_once()

    def test_load_should_succeed_if_record_exists(self, driver, _url, _format, _description, _size_bytes):
        driver.execute_query.return_value = (
            [self.SINGLE_CREATE_RECORDS_RETURN],
            MagicMock(counters=MagicMock(nodes_created=1)),
            ["a"],
        )
        data = Data(driver, _url, _format, _description, _size_bytes)
        assert data.load()
        assert "MATCH (a:Data {url: $url}) RETURN a" in driver.execute_query.call_args[0]
        assert data.url == self.URL
        assert data.format == _format
        assert data.description == _description
        assert data.size_bytes == self.SIZE_BYTES
        assert data.uuid == self.UUID
        assert data.created
        assert data.last_modified

    def test_load_should_return_false_if_record_does_not_exist(self, driver, _url, _format, _description, _size_bytes):
        driver.execute_query.return_value = ([], MagicMock(counters=MagicMock(nodes_created=0)), [])
        data = Data(driver, _url, _format, _description, _size_bytes)
        assert not data.load()
        assert "MATCH (a:Data {url: $url}) RETURN a" in driver.execute_query.call_args[0]
        assert data.url == _url
        assert data.format == _format
        assert data.description == _description
        assert data.size_bytes == _size_bytes
        assert data.uuid is None
        assert data.created is None
        assert data.last_modified is None

    def test_load_should_raise_exception_if_invalid_url(self, driver, _url, _format, _description, _size_bytes):
        data = Data(driver, _url, _format, _description, _size_bytes)
        data.url = None
        with pytest.raises(ValueError):
            data.load()
        data.url = 123
        with pytest.raises(ValueError):
            data.load()

    def test_load_should_raise_exception_if_driver_not_connected(
        self, driver, _url, _format, _description, _size_bytes
    ):
        driver.verify_connectivity.side_effect = Exception("Connection error")
        data = Data(driver, _url, _format, _description, _size_bytes)
        with pytest.raises(Exception):
            data.load()
        driver.verify_connectivity.assert_called_once()

    @pytest.mark.parametrize(
        "query",
        [
            (
                MagicMock(
                    data=lambda: {
                        "a": {
                            "url": "http://arxiv.org",
                            "format": "Computer Science",
                            "description": "A description",
                            "size_bytes": 123456789,
                            "uuid": "",
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
                            "url": "http://arxiv.org",
                            "format": "Computer Science",
                            "description": "A description",
                            "size_bytes": 123456789,
                            "uuid": "1234-5678-9012-3456",
                            "created": "",
                            "last_modified": "2021-01-01T00:00:00",
                        }
                    }
                )
            ),
            (
                MagicMock(
                    data=lambda: {
                        "a": {
                            "url": "http://arxiv.org",
                            "format": "Computer Science",
                            "description": "A description",
                            "size_bytes": 123456789,
                            "uuid": "1234-5678-9012-3456",
                            "created": "2021-01-01T00:00:00",
                            "last_modified": "",
                        }
                    }
                )
            ),
        ],
    )
    def test_load_should_raise_exception_if_returned_values_not_valid(
        self, query, driver, _url, _format, _description, _size_bytes
    ):
        driver.execute_query.return_value = (
            [query],
            MagicMock(counters=MagicMock(nodes_created=1)),
            ["a"],
        )
        data = Data(driver, _url, _format, _description, _size_bytes)
        with pytest.raises(ValueError):
            data.load()
        driver.execute_query.assert_called_once()
        driver.reset_mock()

    def test_find_should_return_data(self, driver, _url, _format, _description, _size_bytes):
        driver.execute_query.return_value = (
            [self.SINGLE_CREATE_RECORDS_RETURN],
            MagicMock(counters=MagicMock(nodes_created=1)),
            ["a"],
        )
        data = Data.find(driver, _url)
        driver.execute_query.assert_called_once()
        assert data.url == self.URL
        assert data.format == _format
        assert data.description == _description
        assert data.uuid == self.UUID
        assert data.created
        assert data.last_modified

    def test_find_should_return_none_if_no_record(self, driver, _url, _format, _description, _size_bytes):
        driver.execute_query.return_value = (
            [MagicMock(data=lambda: {})],
            MagicMock(counters=MagicMock(nodes_created=0)),
            [],
        )
        data = Data.find(driver, _url)
        driver.execute_query.assert_called_once()
        assert data is None

    @pytest.mark.parametrize(
        "d, u",
        [
            (None, "http://arxiv.org"),
            (123, "http://arxiv.org"),
            (MagicMock(spec=Driver), None),
            (MagicMock(spec=Driver), 123),
        ],
    )
    def test_find_should_raise_exception_if_invalid_params(self, d, u):
        with pytest.raises(ValueError):
            Data.find(d, u)

    def test_find_should_raise_exception_if_driver_not_connected(self, driver, _url):
        driver.verify_connectivity.side_effect = Exception("Connection error")
        with pytest.raises(Exception):
            Data.find(driver, _url)
        driver.verify_connectivity.assert_called_once()

    def test_find_all_should_return_datas(self, driver, _url, _format, _description, _size_bytes):
        driver.execute_query.return_value = (
            [
                MagicMock(
                    data=lambda: {
                        "a": {
                            "url": _url,
                            "format": _format,
                            "description": _description,
                            "size_bytes": _size_bytes,
                            "uuid": self.UUID,
                            "created": self.CREATED,
                            "last_modified": self.LAST_MODIFIED,
                        },
                        "b": {
                            "url": _url,
                            "format": _format,
                            "description": _description,
                            "size_bytes": _size_bytes,
                            "uuid": self.UUID,
                            "created": self.CREATED,
                            "last_modified": self.LAST_MODIFIED,
                        },
                    }
                )
            ],
            MagicMock(counters=MagicMock(nodes_created=1)),
            ["a"],
        )
        datas = Data.find_all(driver)
        driver.execute_query.assert_called_once()
        assert len(datas) == 1
        data = datas[0]
        assert data.url == _url
        assert data.format == _format
        assert data.description == _description
        assert data.size_bytes == _size_bytes
        assert data.uuid == self.UUID
        assert data.created
        assert data.last_modified
