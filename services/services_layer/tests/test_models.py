from unittest.mock import MagicMock, patch

import pytest
from neo4j import Driver

from services.services_layer.src.services_layer.models import BaseModel, ArxivSet


class BaseModelChild(BaseModel):
    def create(self):
        pass # required to test instantiate abstract class

    def load(self):
        pass # required to test instantiate abstract class


class TestBaseModel:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.driver_mock = MagicMock(spec=Driver)
        self.driver_mock.verify_connectivity = MagicMock()
        self.base_model = BaseModelChild(self.driver_mock)

    def test_init(self):
        assert self.base_model.driver == self.driver_mock
        assert hasattr(self.base_model, "logger")

    def test_verify_connection_should_success_with_working_driver(self):
        self.base_model.verify_connection()
        self.driver_mock.verify_connectivity.assert_called_once()

    def test_verify_connection_should_raise_exception_when_connection_error(self):
        self.driver_mock.verify_connectivity.side_effect = Exception("Connection error")
        with pytest.raises(Exception, match="Connection error"):
            self.base_model.verify_connection()
        self.driver_mock.verify_connectivity.assert_called_once()

    def test_verify_connection_should_use_logger(self):
        with patch.object(self.base_model.logger, "debug") as logger_debug_mock:
            self.base_model.verify_connection()
            logger_debug_mock.assert_called_once_with(
                "Connection verified", method=self.base_model.verify_connection.__name__
            )

    def test_verify_connection_should_log_errors(self):
        self.driver_mock.verify_connectivity.side_effect = Exception("Connection error")
        with patch.object(self.base_model.logger, "error") as logger_error_mock:
            with pytest.raises(Exception):
                self.base_model.verify_connection()
            logger_error_mock.assert_called_once_with(
                "Connection failed", method=self.base_model.verify_connection.__name__, error="Connection error"
            )

    def test_verify_connection_should_raise_exception_on_init_with_invalid_driver(self):
        invalid_driver = {}
        base_model_invalid = BaseModelChild(self.driver_mock)
        base_model_invalid.driver = invalid_driver
        with pytest.raises(AttributeError):
            base_model_invalid.verify_connection()


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

    @patch("services.services_layer.src.services_layer.models.uuid")
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
        ])
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