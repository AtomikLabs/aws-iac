from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from neo4j import Driver
from orchestration.airflow.dags.shared.utils.constants import S3_KEY_DATE_FORMAT
from orchestration.airflow.dags.shared.models.arxiv_category import ArxivCategory


class TestArxivCategory:

    CS = "CS"
    COMPUTER_SCIENCE = "Computer Science"
    UUID = "1234-5678-9012-3456"
    CREATED = datetime.strptime("2021-01-01T00-00-00", S3_KEY_DATE_FORMAT)
    LAST_MODIFIED = datetime.strptime("2021-01-01T00-00-00", S3_KEY_DATE_FORMAT)

    SINGLE_CREATE_RECORDS_RETURN = MagicMock(
        data=lambda: {
            "a": {
                "code": TestArxivCategory.CS,
                "name": TestArxivCategory.COMPUTER_SCIENCE,
                "uuid": TestArxivCategory.UUID,
                "created": TestArxivCategory.CREATED,
                "last_modified": TestArxivCategory.LAST_MODIFIED,
            }
        }
    )

    @pytest.fixture
    def code(self):
        return TestArxivCategory.CS

    @pytest.fixture
    def driver(self):
        driver = MagicMock(spec=Driver)
        driver.verify_connectivity = MagicMock()
        return driver

    @pytest.fixture
    def name(self):
        return TestArxivCategory.COMPUTER_SCIENCE

    @pytest.fixture
    def uuid_fixture(self):
        return TestArxivCategory.UUID

    @pytest.fixture
    def created_fixture(self):
        return TestArxivCategory.CREATED

    @pytest.fixture
    def last_modified_fixture(self):
        return TestArxivCategory.LAST_MODIFIED

    def test_init_should_succeed_with_valid_params(self, driver, code, name):
        arxiv_category = ArxivCategory(driver, code, name)
        assert arxiv_category.driver == driver
        assert arxiv_category.code == code
        assert arxiv_category.name == name
        assert arxiv_category.uuid is None
        assert arxiv_category.created is None
        assert arxiv_category.last_modified is None

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
            ArxivCategory(d, c, n)

    @patch("orchestration.airflow.dags.shared.models.arxiv_category.uuid")
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
        arxiv_category = ArxivCategory(driver, code, name)
        arxiv_category.create()
        driver.execute_query.assert_called_once()
        assert arxiv_category.uuid == self.UUID
        assert arxiv_category.created
        assert arxiv_category.last_modified
        print(arxiv_category.created)

    @pytest.mark.parametrize(
        "d, c, n",
        [
            (None, "cs", "name"),
            (123, "cs", "name"),
            (MagicMock(spec=Driver), None, "name"),
            (MagicMock(spec=Driver), 123, "name"),
            (MagicMock(spec=Driver), "cs", None),
            (MagicMock(spec=Driver), "cs", 123),
        ],
    )
    def test_create_should_raise_exception_with_invalid_params(self, d, c, n, driver, code, name):
        arxiv_category = ArxivCategory(driver, code, name)
        arxiv_category.code = c
        arxiv_category.name = n
        if not isinstance(d, Driver):
            with pytest.raises(AttributeError):
                arxiv_category.driver = d
                arxiv_category.create()
        else:
            with pytest.raises(ValueError):
                arxiv_category.create()

    def test_create_should_raise_exception_when_no_records_returned(self, driver, code, name):
        driver.execute_query.return_value = ([], MagicMock(counters=MagicMock(nodes_created=0)), [])
        arxiv_category = ArxivCategory(driver, code, name)
        with pytest.raises(RuntimeError):
            arxiv_category.create()
        driver.execute_query.assert_called_once()

    def test_create_should_not_duplicate_ArxivCategory(self, driver, code):
        driver.execute_query.return_value = (
            [self.SINGLE_CREATE_RECORDS_RETURN],
            MagicMock(counters=MagicMock(nodes_created=0)),
            ["a"],
        )
        name = "C0mput3r Sc13nc3"
        arxiv_category = ArxivCategory(driver, code, name)
        arxiv_category.create()
        driver.execute_query.assert_called_once()
        assert arxiv_category.name == self.COMPUTER_SCIENCE

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
        arxiv_category = ArxivCategory(driver, code, name)
        with pytest.raises(ValueError):
            arxiv_category.create()
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
            arxiv_category.create()
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
                            "last_modified": None,
                        }
                    }
                )
            ],
            MagicMock(counters=MagicMock(nodes_created=1)),
            ["a"],
        )
        with pytest.raises(ValueError):
            arxiv_category.create()
        driver.execute_query.assert_called_once()

    def test_load_should_succeed_if_record_exists(self, driver, code, name):
        driver.execute_query.return_value = (
            [self.SINGLE_CREATE_RECORDS_RETURN],
            MagicMock(counters=MagicMock(nodes_created=1)),
            ["a"],
        )
        arxiv_category = ArxivCategory(driver, code, name)
        assert arxiv_category.load()
        assert "MATCH (a:ArxivCategory {code: $code}) RETURN a" in driver.execute_query.call_args[0]
        assert arxiv_category.code == self.CS
        assert arxiv_category.name == name
        assert arxiv_category.uuid == self.UUID
        assert arxiv_category.created
        assert arxiv_category.last_modified

    def test_load_should_return_false_if_record_does_not_exist(self, driver, code, name):
        driver.execute_query.return_value = ([], MagicMock(counters=MagicMock(nodes_created=0)), [])
        arxiv_category = ArxivCategory(driver, code, name)
        assert not arxiv_category.load()
        assert "MATCH (a:ArxivCategory {code: $code}) RETURN a" in driver.execute_query.call_args[0]
        assert arxiv_category.code == code
        assert arxiv_category.name == name
        assert arxiv_category.uuid is None
        assert arxiv_category.created is None
        assert arxiv_category.last_modified is None

    def test_load_should_raise_exception_if_invalid_code(self, driver, code, name):
        arxiv_category = ArxivCategory(driver, code, name)
        arxiv_category.code = None
        with pytest.raises(ValueError):
            arxiv_category.load()
        arxiv_category.code = 123
        with pytest.raises(ValueError):
            arxiv_category.load()

    def test_load_should_raise_exception_if_driver_not_connected(self, driver, code, name):
        driver.verify_connectivity.side_effect = Exception("Connection error")
        arxiv_category = ArxivCategory(driver, code, name)
        with pytest.raises(Exception):
            arxiv_category.load()
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
                            "code": "CS",
                            "name": "Computer Science",
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
                            "code": "CS",
                            "name": "Computer Science",
                            "uuid": "1234-5678-9012-3456",
                            "created": datetime.strptime("2021-01-01T00-00-00", S3_KEY_DATE_FORMAT),
                            "last_modified": None,
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
        arxiv_category = ArxivCategory(driver, code, name)
        with pytest.raises(ValueError):
            arxiv_category.load()
        driver.execute_query.assert_called_once()
        driver.reset_mock()

    def test_find_should_return_arxiv_category(self, driver, code, name):
        driver.execute_query.return_value = (
            [self.SINGLE_CREATE_RECORDS_RETURN],
            MagicMock(counters=MagicMock(nodes_created=1)),
            ["a"],
        )
        arxiv_category = ArxivCategory.find(driver, code)
        driver.execute_query.assert_called_once()
        assert arxiv_category.code == self.CS
        assert arxiv_category.name == name
        assert arxiv_category.uuid == self.UUID
        assert arxiv_category.created
        assert arxiv_category.last_modified

    def test_find_should_return_none_if_no_record(self, driver, code, name):
        driver.execute_query.return_value = (
            [MagicMock(data=lambda: {})],
            MagicMock(counters=MagicMock(nodes_created=0)),
            [],
        )
        arxiv_category = ArxivCategory.find(driver, code)
        driver.execute_query.assert_called_once()
        assert arxiv_category is None

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
            ArxivCategory.find(d, c)

    def test_find_should_raise_exception_if_driver_not_connected(self, driver, code):
        driver.verify_connectivity.side_effect = Exception("Connection error")
        with pytest.raises(Exception):
            ArxivCategory.find(driver, code)
        driver.verify_connectivity.assert_called_once()

    def test_find_all_should_return_arxiv_categories(self, driver, code, name):
        driver.execute_query.return_value = (
            [
                MagicMock(
                    data=lambda: {
                        "a": {
                            "code": code,
                            "name": name,
                            "uuid": self.UUID,
                            "created": self.CREATED,
                            "last_modified": self.LAST_MODIFIED,
                        },
                        "b": {
                            "code": code,
                            "name": name,
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
        arxiv_categories = ArxivCategory.find_all(driver)
        driver.execute_query.assert_called_once()
        assert len(arxiv_categories) == 1
        arxiv_category = arxiv_categories[0]
        assert arxiv_category.code == code
        assert arxiv_category.name == name
        assert arxiv_category.uuid == self.UUID
        assert arxiv_category.created
        assert arxiv_category.last_modified
