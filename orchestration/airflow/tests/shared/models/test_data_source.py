from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from neo4j import Driver
from services.services_layer.src.services_layer.constants import S3_KEY_DATE_FORMAT
from services.services_layer.src.services_layer.models.data_source import DataSource


class TestDataSource:

    URL = "https://arxiv.org"
    NAME = "arxiv"
    DESCRIPTION = "A description"
    UUID = "1234-5678-9012-3456"
    CREATED = datetime.strptime("2021-01-01T00-00-00", S3_KEY_DATE_FORMAT)
    LAST_MODIFIED = datetime.strptime("2021-01-01T00-00-00", S3_KEY_DATE_FORMAT)

    SINGLE_CREATE_RECORDS_RETURN = MagicMock(
        data=lambda: {
            "a": {
                "url": TestDataSource.URL,
                "name": TestDataSource.NAME,
                "description": TestDataSource.DESCRIPTION,
                "uuid": TestDataSource.UUID,
                "created": TestDataSource.CREATED,
                "last_modified": TestDataSource.LAST_MODIFIED,
            }
        }
    )

    @pytest.fixture
    def _url(self):
        return TestDataSource.URL

    @pytest.fixture
    def driver(self):
        driver = MagicMock(spec=Driver)
        driver.verify_connectivity = MagicMock()
        return driver

    @pytest.fixture
    def _name(self):
        return TestDataSource.NAME

    @pytest.fixture
    def _description(self):
        return TestDataSource.DESCRIPTION

    @pytest.fixture
    def uuid_fixture(self):
        return TestDataSource.UUID

    @pytest.fixture
    def created_fixture(self):
        return TestDataSource.CREATED

    @pytest.fixture
    def last_modified_fixture(self):
        return TestDataSource.LAST_MODIFIED

    def test_init_should_succeed_with_valid_params(self, driver, _url, _name, _description):
        data_source = DataSource(driver, _url, _name, _description)
        assert data_source.driver == driver
        assert data_source.url == _url
        assert data_source.name == _name
        assert data_source.description == _description
        assert data_source.uuid is None
        assert data_source.created is None
        assert data_source.last_modified is None

    @pytest.mark.parametrize(
        "d, c, n, desc",
        [
            (None, "cs", "name", "desc"),
            (123, "cs", "name", "desc"),
            (MagicMock(spec=Driver), None, "name", "desc"),
            (MagicMock(spec=Driver), 123, "name", "desc"),
            (MagicMock(spec=Driver), "cs", None, "desc"),
            (MagicMock(spec=Driver), "cs", 123, "desc"),
            (MagicMock(spec=Driver), "cs", "name", None),
            (MagicMock(spec=Driver), "cs", "name", 123),
        ],
    )
    def test_init_should_raise_exception_with_invalid_params(self, d, c, n, desc):
        with pytest.raises(ValueError):
            DataSource(d, c, n, desc)

    @patch("services.services_layer.src.services_layer.models.data_source.uuid")
    def test_create_should_succeed_with_valid_params(self, mock_uuid, driver, _url, _name, _description, uuid_fixture):
        mock_uuid.uuid4 = MagicMock(return_value=uuid_fixture)
        driver.execute_query.return_value = (
            [
                MagicMock(
                    data=lambda: {
                        "a": {
                            "url": self.URL,
                            "name": self.NAME,
                            "description": self.DESCRIPTION,
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
        data_source = DataSource(driver, _url, _name, _description)
        data_source.create()
        driver.execute_query.assert_called_once()
        assert data_source.uuid == self.UUID
        assert data_source.created
        assert data_source.last_modified
        print(data_source.created)

    @pytest.mark.parametrize(
        "d, c, n, desc",
        [
            (None, "cs", "name", "desc"),
            (123, "cs", "name", "desc"),
            (MagicMock(spec=Driver), None, "name", "desc"),
            (MagicMock(spec=Driver), 123, "name", "desc"),
            (MagicMock(spec=Driver), "cs", None, "desc"),
            (MagicMock(spec=Driver), "cs", 123, "desc"),
            (MagicMock(spec=Driver), "cs", "name", None),
            (MagicMock(spec=Driver), "cs", "name", 123),
        ],
    )
    def test_create_should_raise_exception_with_invalid_params(self, d, c, n, desc, driver, _url, _name, _description):
        data_source = DataSource(driver, _url, _name, _description)
        data_source.url = c
        data_source.name = n
        data_source.description = desc
        if not isinstance(d, Driver):
            with pytest.raises(AttributeError):
                data_source.driver = d
                data_source.create()
        else:
            with pytest.raises(ValueError):
                data_source.driver = driver
                data_source.create()

    def test_create_should_raise_exception_when_no_records_returned(self, driver, _url, _name, _description):
        driver.execute_query.return_value = ([], MagicMock(counters=MagicMock(nodes_created=0)), [])
        data_source = DataSource(driver, _url, _name, _description)
        with pytest.raises(RuntimeError):
            data_source.create()
        driver.execute_query.assert_called_once()

    def test_create_should_not_duplicate_data_source(self, driver, _url, _name, _description):
        driver.execute_query.return_value = (
            [self.SINGLE_CREATE_RECORDS_RETURN],
            MagicMock(counters=MagicMock(nodes_created=0)),
            ["a"],
        )
        name = "C0mput3r Sc13nc3"
        data_source = DataSource(driver, _url, name, _description)
        data_source.create()
        driver.execute_query.assert_called_once()
        assert data_source.name == _name

    def test_create_should_raise_exception_if_record_improperly_created(self, driver, _url, _name, _description):
        driver.execute_query.return_value = (
            [
                MagicMock(
                    data=lambda: {
                        "a": {
                            "url": self.URL,
                            "name": self.NAME,
                            "description": self.DESCRIPTION,
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
        data_source = DataSource(driver, _url, _name, _description)
        with pytest.raises(ValueError):
            data_source.create()
        driver.execute_query.assert_called_once()
        driver.reset_mock()
        driver.execute_query.return_value = (
            [
                MagicMock(
                    data=lambda: {
                        "a": {
                            "url": self.URL,
                            "name": self.NAME,
                            "description": self.DESCRIPTION,
                            "uuid": self.UUID,
                            "created": None,
                            "last_modified": self.LAST_MODIFIED,
                        }
                    }
                )
            ],
            MagicMock(counters=MagicMock(nodes_created=1)),
            ["a"],
        )
        with pytest.raises(ValueError):
            data_source.create()
        driver.execute_query.assert_called_once()
        driver.reset_mock()
        driver.execute_query.return_value = (
            [
                MagicMock(
                    data=lambda: {
                        "a": {
                            "url": self.URL,
                            "name": self.NAME,
                            "description": self.DESCRIPTION,
                            "uuid": self.UUID,
                            "created": self.CREATED,
                            "last_modified": None,
                        }
                    }
                )
            ],
            MagicMock(counters=MagicMock(nodes_created=1)),
            ["a"],
        )
        with pytest.raises(ValueError):
            data_source.create()
        driver.execute_query.assert_called_once()

    def test_load_should_succeed_if_record_exists(self, driver, _url, _name, _description):
        driver.execute_query.return_value = (
            [self.SINGLE_CREATE_RECORDS_RETURN],
            MagicMock(counters=MagicMock(nodes_created=1)),
            ["a"],
        )
        data_source = DataSource(driver, _url, _name, _description)
        assert data_source.load()
        assert "MATCH (a:DataSource {url: $url}) RETURN a" in driver.execute_query.call_args[0]
        assert data_source.url == self.URL
        assert data_source.name == _name
        assert data_source.description == _description
        assert data_source.uuid == self.UUID
        assert data_source.created
        assert data_source.last_modified

    def test_load_should_return_false_if_record_does_not_exist(self, driver, _url, _name, _description):
        driver.execute_query.return_value = ([], MagicMock(counters=MagicMock(nodes_created=0)), [])
        data_source = DataSource(driver, _url, _name, _description)
        assert not data_source.load()
        assert "MATCH (a:DataSource {url: $url}) RETURN a" in driver.execute_query.call_args[0]
        assert data_source.url == _url
        assert data_source.name == _name
        assert data_source.description == _description
        assert data_source.uuid is None
        assert data_source.created is None
        assert data_source.last_modified is None

    def test_load_should_raise_exception_if_invalid_url(self, driver, _url, _name, _description):
        data_source = DataSource(driver, _url, _name, _description)
        data_source.url = None
        with pytest.raises(ValueError):
            data_source.load()
        data_source.url = 123
        with pytest.raises(ValueError):
            data_source.load()

    def test_load_should_raise_exception_if_driver_not_connected(self, driver, _url, _name, _description):
        driver.verify_connectivity.side_effect = Exception("Connection error")
        data_source = DataSource(driver, _url, _name, _description)
        with pytest.raises(Exception):
            data_source.load()
        driver.verify_connectivity.assert_called_once()

    @pytest.mark.parametrize(
        "query",
        [
            (
                MagicMock(
                    data=lambda: {
                        "a": {
                            "url": "CS",
                            "name": "Computer Science",
                            "description": "A description",
                            "uuid": "",
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
                            "url": "CS",
                            "name": "Computer Science",
                            "description": "A description",
                            "uuid": "1234-5678-9012-3456",
                            "created": None,
                            "last_modified": datetime.strptime("2021-01-01T00-00-00", S3_KEY_DATE_FORMAT),
                        }
                    }
                )
            ),
            (
                MagicMock(
                    data=lambda: {
                        "a": {
                            "url": "CS",
                            "name": "Computer Science",
                            "description": "A description",
                            "uuid": "1234-5678-9012-3456",
                            "created": datetime.strptime("2021-01-01T00-00-00", S3_KEY_DATE_FORMAT),
                            "last_modified": None,
                        }
                    }
                )
            ),
        ],
    )
    def test_load_should_raise_exception_if_returned_values_not_valid(self, query, driver, _url, _name, _description):
        driver.execute_query.return_value = (
            [query],
            MagicMock(counters=MagicMock(nodes_created=1)),
            ["a"],
        )
        data_source = DataSource(driver, _url, _name, _description)
        with pytest.raises(ValueError):
            data_source.load()
        driver.execute_query.assert_called_once()
        driver.reset_mock()

    def test_find_should_return_data_source(self, driver, _url, _name, _description):
        driver.execute_query.return_value = (
            [self.SINGLE_CREATE_RECORDS_RETURN],
            MagicMock(counters=MagicMock(nodes_created=1)),
            ["a"],
        )
        data_source = DataSource.find(driver, _url)
        driver.execute_query.assert_called_once()
        assert data_source.url == self.URL
        assert data_source.name == _name
        assert data_source.description == _description
        assert data_source.uuid == self.UUID
        assert data_source.created
        assert data_source.last_modified

    def test_find_should_return_none_if_no_record(self, driver, _url, _name, _description):
        driver.execute_query.return_value = (
            [MagicMock(data=lambda: {})],
            MagicMock(counters=MagicMock(nodes_created=0)),
            [],
        )
        data_source = DataSource.find(driver, _url)
        driver.execute_query.assert_called_once()
        assert data_source is None

    @pytest.mark.parametrize(
        "d, c",
        [
            (None, "CS"),
            (123, "CS"),
            (MagicMock(spec=Driver), None),
            (MagicMock(spec=Driver), 123),
        ],
    )
    def test_find_should_raise_exception_if_invalid_params(self, d, c):
        with pytest.raises(ValueError):
            DataSource.find(d, c)

    def test_find_should_raise_exception_if_driver_not_connected(self, driver, _url):
        driver.verify_connectivity.side_effect = Exception("Connection error")
        with pytest.raises(Exception):
            DataSource.find(driver, _url)
        driver.verify_connectivity.assert_called_once()

    def test_find_all_should_return_data_sources(self, driver, _url, _name, _description):
        driver.execute_query.return_value = (
            [
                MagicMock(
                    data=lambda: {
                        "a": {
                            "url": _url,
                            "name": _name,
                            "description": _description,
                            "uuid": self.UUID,
                            "created": self.CREATED,
                            "last_modified": self.LAST_MODIFIED,
                        },
                        "b": {
                            "url": _url,
                            "name": _name,
                            "description": _description,
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
        data_sources = DataSource.find_all(driver)
        driver.execute_query.assert_called_once()
        assert len(data_sources) == 1
        data_source = data_sources[0]
        assert data_source.url == _url
        assert data_source.name == _name
        assert data_source.description == _description
        assert data_source.uuid == self.UUID
        assert data_source.created
        assert data_source.last_modified
