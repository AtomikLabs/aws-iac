from unittest.mock import MagicMock, patch

import pytest
from neo4j import Driver

from services.services_layer.src.services_layer.models.data_operation import DataOperation


class TestDataOperation:

    NAME = "DataOperation"
    METHOD_NAME = "method_name"
    METHOD_VERSION = "method_version"
    UUID = "1234-5678-9012-3456"
    CREATED = "2021-01-01T00:00:00"
    LAST_MODIFIED = "2021-01-01T00:00:00"

    SINGLE_CREATE_RECORDS_RETURN = MagicMock(
        data=lambda: {
            "a": {
                "name": TestDataOperation.NAME,
                "method_name": TestDataOperation.METHOD_NAME,
                "method_version": TestDataOperation.METHOD_VERSION,
                "uuid": TestDataOperation.UUID,
                "created": TestDataOperation.CREATED,
                "last_modified": TestDataOperation.LAST_MODIFIED,
            }
        }
    )

    @pytest.fixture
    def _driver(self):
        driver = MagicMock(spec=Driver)
        driver.verify_connectivity = MagicMock()
        return driver

    @pytest.fixture
    def _method_name(self):
        return TestDataOperation.METHOD_NAME

    @pytest.fixture
    def _method_version(self):
        return TestDataOperation.METHOD_VERSION

    @pytest.fixture
    def _name(self):
        return TestDataOperation.NAME

    @pytest.fixture
    def _uuid_fixture(self):
        return TestDataOperation.UUID

    @pytest.fixture
    def _created_fixture(self):
        return TestDataOperation.CREATED

    @pytest.fixture
    def _last_modified_fixture(self):
        return TestDataOperation.LAST_MODIFIED

    def test_init_should_succeed_with_valid_params(self, _driver, _name, _method_name, _method_version):
        data_operation = DataOperation(_driver, _name, _method_name, _method_version)
        assert data_operation.driver == _driver
        assert data_operation.method_name == _method_name
        assert data_operation.method_version == _method_version
        assert data_operation.name == _name
        assert data_operation.uuid is None
        assert data_operation.created is None
        assert data_operation.last_modified is None

    @pytest.mark.parametrize(
        "d, n, m_n, m_v",
        [
            (None, "name", "method_name", "method_version"),
            (123, "name", "method_name", "method_version"),
            (MagicMock(spec=Driver), None, "method_name", "method_version"),
            (MagicMock(spec=Driver), 123, "method_name", "method_version"),
            (MagicMock(spec=Driver), "name", None, "method_version"),
            (MagicMock(spec=Driver), "name", 123, "method_version"),
            (MagicMock(spec=Driver), "name", "method_name", None),
            (MagicMock(spec=Driver), "name", "method_name", 123),
        ],
    )
    def test_init_should_raise_exception_with_invalid_params(self, d, n, m_n, m_v):
        with pytest.raises(ValueError):
            DataOperation(d, n, m_n, m_v)

    @patch("services.services_layer.src.services_layer.models.data_operation.uuid")
    def test_create_should_succeed_with_valid_params(
        self, mock_uuid, _driver, _name, _method_name, _method_version, _uuid_fixture
    ):
        mock_uuid.uuid4 = MagicMock(return_value=_uuid_fixture)
        _driver.execute_query.return_value = (
            [
                MagicMock(
                    data=lambda: {
                        "a": {
                            "name": self.NAME,
                            "method_name": self.METHOD_NAME,
                            "method_version": self.METHOD_VERSION,
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
        data_operation = DataOperation(_driver, _name, _method_name, _method_version)
        data_operation.create()
        _driver.execute_query.assert_called_once()
        assert data_operation.uuid == self.UUID
        assert data_operation.created
        assert data_operation.last_modified
        print(data_operation.created)

    @pytest.mark.parametrize(
        "d, n, m_n, m_v",
        [
            (None, "name", "method_name", "method_version"),
            (123, "name", "method_name", "method_version"),
            (MagicMock(spec=Driver), None, "method_name", "method_version"),
            (MagicMock(spec=Driver), 123, "method_name", "method_version"),
            (MagicMock(spec=Driver), "name", None, "method_version"),
            (MagicMock(spec=Driver), "name", 123, "method_version"),
            (MagicMock(spec=Driver), "name", "method_name", None),
            (MagicMock(spec=Driver), "name", "method_name", 123),
        ],
    )
    def test_create_should_raise_exception_with_invalid_params(
        self, d, n, m_n, m_v, _driver, _name, _method_name, _method_version
    ):
        data_operation = DataOperation(_driver, _name, _method_name, _method_version)
        data_operation.name = n
        data_operation.method_name = m_n
        data_operation.method_version = m_v
        if not isinstance(d, Driver):
            with pytest.raises(AttributeError):
                data_operation.driver = d
                data_operation.create()
        else:
            with pytest.raises(ValueError):
                data_operation.driver = _driver
                data_operation.create()

    def test_create_should_raise_exception_when_no_records_returned(
        self, _driver, _name, _method_name, _method_version
    ):
        _driver.execute_query.return_value = ([], MagicMock(counters=MagicMock(nodes_created=0)), [])
        data_operation = DataOperation(_driver, _name, _method_name, _method_version)
        with pytest.raises(RuntimeError):
            data_operation.create()
        _driver.execute_query.assert_called_once()

    def test_create_should_not_duplicate_data_operation(self, _driver, _name, _method_name, _method_version):
        _driver.execute_query.return_value = (
            [self.SINGLE_CREATE_RECORDS_RETURN],
            MagicMock(counters=MagicMock(nodes_created=0)),
            ["a"],
        )
        name = "C0mput3r Sc13nc3"
        data_operation = DataOperation(_driver, name, _method_name, _method_version)
        data_operation.create()
        _driver.execute_query.assert_called_once()
        assert data_operation.name == _name

    def test_create_should_raise_exception_if_record_improperly_created(
        self, _driver, _name, _method_name, _method_version
    ):
        _driver.execute_query.return_value = (
            [
                MagicMock(
                    data=lambda: {
                        "a": {
                            "name": self.NAME,
                            "method_name": self.METHOD_NAME,
                            "method_version": self.METHOD_VERSION,
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
        data_operation = DataOperation(_driver, _name, _method_name, _method_version)
        with pytest.raises(ValueError):
            data_operation.create()
        _driver.execute_query.assert_called_once()
        _driver.reset_mock()
        _driver.execute_query.return_value = (
            [
                MagicMock(
                    data=lambda: {
                        "a": {
                            "name": self.NAME,
                            "uuid": self.UUID,
                            "method_name": self.METHOD_NAME,
                            "method_version": self.METHOD_VERSION,
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
            data_operation.create()
        _driver.execute_query.assert_called_once()
        _driver.reset_mock()
        _driver.execute_query.return_value = (
            [
                MagicMock(
                    data=lambda: {
                        "a": {
                            "name": self.NAME,
                            "method_name": self.METHOD_NAME,
                            "method_version": self.METHOD_VERSION,
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
            data_operation.create()
        _driver.execute_query.assert_called_once()
