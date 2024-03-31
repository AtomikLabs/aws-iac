from unittest.mock import MagicMock, patch

import pytest
from neo4j import Driver

from services.services_layer.src.services_layer.models.base_model import BaseModel

class BaseModelChild(BaseModel):
    def create(self):
        pass  # required to test instantiate abstract class

    @classmethod
    def find(cls, driver: Driver):
        pass # required to test instantiate abstract class

    @classmethod
    def find_all(cls, driver: Driver):
        pass # required to test instantiate abstract class

    def load(self):
        pass  # required to test instantiate abstract class


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