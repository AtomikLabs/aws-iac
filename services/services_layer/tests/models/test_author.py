from unittest.mock import MagicMock, patch

import pytest
from neo4j import Driver

from services.services_layer.src.services_layer.models.author import Author


class TestAuthor:

    LAST_NAME = "Doe"
    FIRST_NAME = "John"
    LAST_NAME_2 = "Smith"
    FIRST_NAME_2 = "Jane"
    UUID = "1234-5678-9012-3456"
    CREATED = "2021-01-01T00:00:00"
    LAST_MODIFIED = "2021-01-01T00:00:00"

    SINGLE_CREATE_RECORDS_RETURN = MagicMock(
        data=lambda: {
            "a": {
                "last_name": TestAuthor.LAST_NAME,
                "first_name": TestAuthor.FIRST_NAME,
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
    def _last_name(self):
        return TestAuthor.LAST_NAME

    @pytest.fixture
    def _first_name(self):
        return TestAuthor.FIRST_NAME

    @pytest.fixture
    def _last_name_2(self):
        return TestAuthor.LAST_NAME_2

    @pytest.fixture
    def _first_name_2(self):
        return TestAuthor.FIRST_NAME_2

    @pytest.fixture
    def _uuid(self):
        return TestAuthor.UUID

    def test_init_should_succeed_with_valid_params(self, driver, _last_name, _first_name):
        author = Author(driver, _last_name, _first_name)
        assert author.driver == driver
        assert author.last_name == _last_name
        assert author.first_name == _first_name
        assert author.uuid is None
        assert author.created is None
        assert author.last_modified is None

    @pytest.mark.parametrize(
        "d, la, f",
        [
            (None, "Doe", "John"),
            (123, "Smith", "Jane"),
            (MagicMock(spec=Driver), 123, "Jane"),
            (MagicMock(spec=Driver), "Smith", 123),
        ],
    )
    def test_init_should_raise_exception_with_invalid_params(self, d, la, f):
        with pytest.raises(ValueError):
            Author(d, la, f)

    @patch("services.services_layer.src.services_layer.models.author.uuid")
    def test_create_should_succeed_with_valid_params(
        self,
        mock_uuid,
        driver,
        _last_name,
        _first_name,
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
                            "last_name": _last_name,
                            "first_name": _first_name,
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
        author = Author(driver, _last_name, _first_name)
        author.create()
        driver.execute_query.assert_called_once()
        assert author.last_name == _last_name
        assert author.first_name == _first_name
        assert author.uuid == _uuid
        assert author.created == _created
        assert author.last_modified == _last_modified

    @pytest.mark.parametrize(
        "d, ln, f",
        [
            (None, "Doe", "John"),
            (123, "Smith", "Jane"),
            (MagicMock(spec=Driver), 123, "Jane"),
            (MagicMock(spec=Driver), "Smith", 123),
        ],
    )
    def test_create_should_raise_exception_with_invalid_params(self, d, ln, f, driver, _last_name, _first_name):
        author = Author(driver, _last_name, _first_name)
        author.last_name = ln
        author.first_name = f
        if not isinstance(d, Driver):
            with pytest.raises(AttributeError):
                author.driver = d
                author.create()
        else:
            with pytest.raises(ValueError):
                author.create()

    def test_create_should_raise_exception_when_no_records_returned(self, driver, _last_name, _first_name):
        driver.execute_query.return_value = ([], MagicMock(counters=MagicMock(nodes_created=0)), [])
        author = Author(driver, _last_name, _first_name)
        with pytest.raises(RuntimeError):
            author.create()
        driver.execute_query.assert_called_once()

    def test_create_should_not_duplicate_Author(self, driver, _last_name, _first_name):
        driver.execute_query.return_value = (
            [self.SINGLE_CREATE_RECORDS_RETURN],
            MagicMock(counters=MagicMock(nodes_created=0)),
            ["a"],
        )
        first_name = "Møøse"
        author = Author(driver, _last_name, _first_name)
        author.first_name = first_name
        author.create()
        driver.execute_query.assert_called_once()
        assert author.first_name == _first_name

    def test_create_should_raise_exception_if_record_improperly_created(
        self, driver, _last_name, _first_name, _uuid, _created, _last_modified
    ):
        driver.execute_query.return_value = (
            [
                MagicMock(
                    data=lambda: {
                        "a": {
                            "last_name": _last_name,
                            "first_name": _first_name,
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
        author = Author(driver, _last_name, _first_name)
        with pytest.raises(ValueError):
            author.create()
        driver.execute_query.assert_called_once()
        driver.reset_mock()
        driver.execute_query.return_value = (
            [
                MagicMock(
                    data=lambda: {
                        "a": {
                            "last_name": _last_name,
                            "first_name": _first_name,
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
                            "last_name": _last_name,
                            "first_name": _first_name,
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
        _last_name,
        _first_name,
        _uuid,
        _created,
        _last_modified,
    ):
        driver.execute_query.return_value = (
            [self.SINGLE_CREATE_RECORDS_RETURN],
            MagicMock(counters=MagicMock(nodes_created=1)),
            ["a"],
        )
        author = Author(driver, _last_name, _first_name)
        assert author.load()
        assert (
            "MATCH (a:Author {last_name: $last_name, first_name: $first_name}) RETURN a"
            in driver.execute_query.call_args[0]
        )
        assert author.last_name == _last_name
        assert author.first_name == _first_name
        assert author.uuid == _uuid
        assert author.created == _created
        assert author.last_modified == _last_modified

    def test_load_should_return_false_if_record_does_not_exist(self, driver, _last_name, _first_name):
        driver.execute_query.return_value = ([], MagicMock(counters=MagicMock(nodes_created=0)), [])
        author = Author(driver, _last_name, _first_name)
        assert not author.load()
        assert (
            "MATCH (a:Author {last_name: $last_name, first_name: $first_name}) RETURN a"
            in driver.execute_query.call_args[0]
        )
        assert author.last_name == _last_name
        assert author.first_name == _first_name
        assert author.uuid is None
        assert author.created is None
        assert author.last_modified is None

    def test_load_should_raise_exception_if_invalid_last_name(self, driver, _last_name, _first_name):
        author = Author(driver, _last_name, _first_name)
        author.last_name = None
        with pytest.raises(ValueError):
            author.load()
        author.last_name = 123
        with pytest.raises(ValueError):
            author.load()

    def test_load_should_raise_exception_if_driver_not_connected(self, driver, _last_name, _first_name):
        driver.verify_connectivity.side_effect = Exception("Connection error")
        author = Author(driver, _last_name, _first_name)
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
                            "last_name": "",
                            "first_name": "This is a test author",
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
                            "last_name": "",
                            "first_name": "This is a test author",
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
                            "last_name": "",
                            "first_name": "This is a test author",
                            "uuid": "1234-5678-9012-3456",
                            "created": "2021-01-01T00:00:00",
                            "last_modified": "2021-01-01T00:00:00",
                        }
                    }
                )
            ),
        ],
    )
    def test_load_should_raise_exception_if_returned_values_not_valid(self, query, driver, _last_name, _first_name):
        driver.execute_query.return_value = (
            [query],
            MagicMock(counters=MagicMock(nodes_created=1)),
            ["a"],
        )
        author = Author(driver, _last_name, _first_name)
        with pytest.raises(ValueError):
            author.load()
        driver.execute_query.assert_called_once()
        driver.reset_mock()

    def test_find_should_return_author(self, driver, _last_name, _first_name, _uuid, _created, _last_modified):
        driver.execute_query.return_value = (
            [self.SINGLE_CREATE_RECORDS_RETURN],
            MagicMock(counters=MagicMock(nodes_created=1)),
            ["a"],
        )
        author = Author.find(driver, _last_name, _first_name)
        driver.execute_query.assert_called_once()
        assert author.last_name == _last_name
        assert author.first_name == _first_name
        assert author.uuid == _uuid
        assert author.created == _created
        assert author.last_modified == _last_modified

    def test_find_should_return_none_if_no_record(self, driver, _last_name, _first_name):
        driver.execute_query.return_value = (
            [MagicMock(data=lambda: {})],
            MagicMock(counters=MagicMock(nodes_created=0)),
            [],
        )
        author = Author.find(driver, _last_name, _first_name)
        driver.execute_query.assert_called_once()
        assert author is None

    @pytest.mark.parametrize(
        "d, ln, f",
        [
            (None, "Doe", "John"),
            (MagicMock(spec=Driver), 123, "Jane"),
            (MagicMock(spec=Driver), "Smith", 123),
        ],
    )
    def test_find_should_raise_exception_if_invalid_params(self, d, ln, f):
        with pytest.raises(ValueError):
            Author.find(d, ln, f)

    def test_find_should_raise_exception_if_driver_not_connected(self, driver, _last_name, _first_name):
        driver.verify_connectivity.side_effect = Exception("Connection error")
        with pytest.raises(Exception):
            Author.find(driver, _last_name, _first_name)
        driver.verify_connectivity.assert_called_once()

    def test_find_all_should_should_turn_all_found_records(
        self, driver, _last_name, _first_name, _uuid, _created, _last_modified
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
            assert author.last_name == _last_name
            assert author.first_name == _first_name
            assert author.uuid == _uuid
            assert author.created == _created
            assert author.last_modified == _last_modified
