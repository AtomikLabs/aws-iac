from unittest.mock import MagicMock, patch

import pytest
from neo4j import Driver

from services.services_layer.src.services_layer.models.arxiv_set import ArxivSet

class TestArixSet:

    CS = "CS"
    COMPUTER_SCIENCE = "Computer Science"
    UUID = "1234-5678-9012-3456"
    CREATED = "2021-01-01T00:00:00"
    LAST_MODIFIED = "2021-01-01T00:00:00"

    SINGLE_CREATE_RECORDS_RETURN = MagicMock(
        data=lambda: {
            "a": {
                "code": TestArixSet.CS,
                "name": TestArixSet.COMPUTER_SCIENCE,
                "uuid": TestArixSet.UUID,
                "created": TestArixSet.CREATED,
                "last_modified": TestArixSet.LAST_MODIFIED,
            }
        }
    )

    @pytest.fixture
    def code(self):
        return TestArixSet.CS

    @pytest.fixture
    def driver(self):
        driver = MagicMock(spec=Driver)
        driver.verify_connectivity = MagicMock()
        return driver

    @pytest.fixture
    def name(self):
        return TestArixSet.COMPUTER_SCIENCE

    @pytest.fixture
    def uuid_fixture(self):
        return TestArixSet.UUID

    @pytest.fixture
    def created_fixture(self):
        return TestArixSet.CREATED

    @pytest.fixture
    def last_modified_fixture(self):
        return TestArixSet.LAST_MODIFIED

    def test_init_should_succeed_with_valid_params(self, driver, code, name):
        arxiv_set = ArxivSet(driver, code, name)
        assert arxiv_set.driver == driver
        assert arxiv_set.code == code
        assert arxiv_set.name == name
        assert arxiv_set.uuid is None
        assert arxiv_set.created is None
        assert arxiv_set.last_modified is None

    @pytest.mark.parametrize(
        "d, c, n",
        [
            (None, "cs", "name"),
            (123, "cs", "name"),
            (MagicMock(), None, "name"),
            (MagicMock(), 123, "name"),
            (MagicMock(), "cs", None),
            (MagicMock(), "cs", 123),
        ],
    )
    def test_init_should_raise_exception_with_invalid_params(self, d, c, n):
        with pytest.raises(ValueError):
            ArxivSet(d, c, n)

    @patch("services.services_layer.src.services_layer.models.arxiv_set.uuid")
    def test_create_should_succeed_with_valid_params(self, mock_uuid, driver, code, name, uuid_fixture):
        mock_uuid.uuid4 = MagicMock(return_value=uuid_fixture)
        driver.execute_query.return_value = (
            [
                MagicMock(
                    data=lambda: {
                        "a": {
                            "code": self.CS,
                            "name": self.COMPUTER_SCIENCE,
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
        arxiv_set = ArxivSet(driver, code, name)
        arxiv_set.create()
        driver.execute_query.assert_called_once()
        assert arxiv_set.uuid == self.UUID
        assert arxiv_set.created
        assert arxiv_set.last_modified
        print(arxiv_set.created)

    @pytest.mark.parametrize(
        "d, c, n",
        [
            (None, "cs", "name"),
            (123, "cs", "name"),
            (MagicMock(), None, "name"),
            (MagicMock(), 123, "name"),
            (MagicMock(), "cs", None),
            (MagicMock(), "cs", 123),
        ],
    )
    def test_create_should_raise_exception_with_invalid_params(self, d, c, n, driver, code, name):
        arxiv_set = ArxivSet(driver, code, name)
        with pytest.raises(ValueError):
            arxiv_set.driver = driver
            arxiv_set.code = code
            arxiv_set.name = name
            arxiv_set.create()

    def test_create_should_raise_exception_when_no_records_returned(self, driver, code, name):
        driver.execute_query.return_value = ([], MagicMock(counters=MagicMock(nodes_created=0)), [])
        arxiv_set = ArxivSet(driver, code, name)
        with pytest.raises(RuntimeError):
            arxiv_set.create()
        driver.execute_query.assert_called_once()

    def test_create_should_not_duplicate_arxivset(self, driver, code):
        driver.execute_query.return_value = (
            [self.SINGLE_CREATE_RECORDS_RETURN],
            MagicMock(counters=MagicMock(nodes_created=0)),
            ["a"],
        )
        name = "C0mput3r Sc13nc3"
        arxiv_set = ArxivSet(driver, code, name)
        arxiv_set.create()
        driver.execute_query.assert_called_once()
        assert arxiv_set.name == self.COMPUTER_SCIENCE

    def test_create_should_raise_exception_if_record_improperly_created(self, driver, code, name):
        driver.execute_query.return_value = (
            [
                MagicMock(
                    data=lambda: {
                        "a": {
                            "code": self.CS,
                            "name": self.COMPUTER_SCIENCE,
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
        arxiv_set = ArxivSet(driver, code, name)
        with pytest.raises(ValueError):
            arxiv_set.create()
        driver.execute_query.assert_called_once()
        driver.reset_mock()
        driver.execute_query.return_value = (
            [
                MagicMock(
                    data=lambda: {
                        "a": {
                            "code": self.CS,
                            "name": self.COMPUTER_SCIENCE,
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
            arxiv_set.create()
        driver.execute_query.assert_called_once()
        driver.reset_mock()
        driver.execute_query.return_value = (
            [
                MagicMock(
                    data=lambda: {
                        "a": {
                            "code": self.CS,
                            "name": self.COMPUTER_SCIENCE,
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
            arxiv_set.create()
        driver.execute_query.assert_called_once()

    def test_load_should_succeed_if_record_exists(self, driver, code, name):
        driver.execute_query.return_value = (
            [self.SINGLE_CREATE_RECORDS_RETURN],
            MagicMock(counters=MagicMock(nodes_created=1)),
            ["a"],
        )
        arxiv_set = ArxivSet(driver, code, name)
        assert arxiv_set.load()
        assert "MATCH (a:ArxivSet {code: $code}) RETURN a" in driver.execute_query.call_args[0]
        assert arxiv_set.code == self.CS
        assert arxiv_set.name == name
        assert arxiv_set.uuid == self.UUID
        assert arxiv_set.created
        assert arxiv_set.last_modified

    def test_load_should_return_false_if_record_does_not_exist(self, driver, code, name):
        driver.execute_query.return_value = ([], MagicMock(counters=MagicMock(nodes_created=0)), [])
        arxiv_set = ArxivSet(driver, code, name)
        assert not arxiv_set.load()
        assert "MATCH (a:ArxivSet {code: $code}) RETURN a" in driver.execute_query.call_args[0]
        assert arxiv_set.code == code
        assert arxiv_set.name == name
        assert arxiv_set.uuid is None
        assert arxiv_set.created is None
        assert arxiv_set.last_modified is None

    def test_load_should_raise_exception_if_invalid_code(self, driver, code, name):
        arxiv_set = ArxivSet(driver, code, name)
        arxiv_set.code = None
        with pytest.raises(ValueError):
            arxiv_set.load()
        arxiv_set.code = 123
        with pytest.raises(ValueError):
            arxiv_set.load()

    def test_load_should_raise_exception_if_driver_not_connected(self, driver, code, name):
        driver.verify_connectivity.side_effect = Exception("Connection error")
        arxiv_set = ArxivSet(driver, code, name)
        with pytest.raises(Exception):
            arxiv_set.load()
        driver.verify_connectivity.assert_called_once()

    @pytest.mark.parametrize(
        "query",
        [
            (
                MagicMock(
                    data=lambda: {
                        "a": {
                            "code": "CS",
                            "name": "Computer Science",
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
                            "code": "CS",
                            "name": "Computer Science",
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
                            "code": "CS",
                            "name": "Computer Science",
                            "uuid": "1234-5678-9012-3456",
                            "created": "2021-01-01T00:00:00",
                            "last_modified": "",
                        }
                    }
                )
            ),
        ],
    )
    def test_load_should_raise_exception_if_returned_values_not_valid(self, query, driver, code, name):
        driver.execute_query.return_value = (
            [query],
            MagicMock(counters=MagicMock(nodes_created=1)),
            ["a"],
        )
        arxiv_set = ArxivSet(driver, code, name)
        with pytest.raises(ValueError):
            arxiv_set.load()
        driver.execute_query.assert_called_once()
        driver.reset_mock()

    def test_find_should_return_arxiv_set(self, driver, code, name):
        driver.execute_query.return_value = (
            [self.SINGLE_CREATE_RECORDS_RETURN],
            MagicMock(counters=MagicMock(nodes_created=1)),
            ["a"],
        )
        arxiv_set = ArxivSet.find(driver, code)
        driver.execute_query.assert_called_once()
        assert arxiv_set.code == self.CS
        assert arxiv_set.name == name
        assert arxiv_set.uuid == self.UUID
        assert arxiv_set.created
        assert arxiv_set.last_modified

    def test_find_should_return_none_if_no_record(self, driver, code, name):
        driver.execute_query.return_value = ([MagicMock(data=lambda: {})], MagicMock(counters=MagicMock(nodes_created=0)), [])
        arxiv_set = ArxivSet.find(driver, code)
        driver.execute_query.assert_called_once()
        assert arxiv_set is None
    
    @pytest.mark.parametrize(
        "d, c",
        [
            (None, "CS"),
            (123, "CS"),
            (MagicMock(), None),
            (MagicMock(), 123),
        ],
    )
    def test_find_should_raise_exception_if_invalid_params(self, d, c):
        with pytest.raises(ValueError):
            ArxivSet.find(d, c)
    
    def test_find_should_raise_exception_if_driver_not_connected(self, driver, code):
        driver.verify_connectivity.side_effect = Exception("Connection error")
        with pytest.raises(Exception):
            ArxivSet.find(driver, code)
        driver.verify_connectivity.assert_called_once()
    
    def test_find_all_should_return_arxiv_sets(self, driver, code, name):
        driver.execute_query.return_value = (
            [MagicMock(data=lambda: {
                "a": {
                    "code": code,
                    "name": name,
                    "uuid": self.UUID,
                    "created": self.CREATED,
                    "last_modified": self.LAST_MODIFIED
                },
                "b": {
                    "code": code,
                    "name": name,
                    "uuid": self.UUID,
                    "created": self.CREATED,
                    "last_modified": self.LAST_MODIFIED
                }})],
            MagicMock(counters=MagicMock(nodes_created=1)),
            ["a"],
        )
        arxiv_sets = ArxivSet.find_all(driver)
        driver.execute_query.assert_called_once()
        assert len(arxiv_sets) == 1
        arxiv_set = arxiv_sets[0]
        assert arxiv_set.code == code
        assert arxiv_set.name == name
        assert arxiv_set.uuid == self.UUID
        assert arxiv_set.created
        assert arxiv_set.last_modified