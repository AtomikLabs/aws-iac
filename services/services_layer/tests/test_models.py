import pytest
from unittest.mock import MagicMock, patch
from neo4j import GraphDatabase
from services.services_layer.src.services_layer.models import BaseModel

class TestBaseModel:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.driver_mock = MagicMock(spec=GraphDatabase.driver)
        self.driver_mock.verify_connectivity = MagicMock()
        self.base_model = BaseModel(self.driver_mock)

    def test_init(self):
        assert self.base_model.driver == self.driver_mock
        assert hasattr(self.base_model, 'logger')

    def test_verify_connection_success(self):
        self.base_model.verify_connection()
        self.driver_mock.verify_connectivity.assert_called_once()

    def test_verify_connection_failure(self):
        self.driver_mock.verify_connectivity.side_effect = Exception("Connection error")
        with pytest.raises(Exception, match="Connection error"):
            self.base_model.verify_connection()
        self.driver_mock.verify_connectivity.assert_called_once()

    def test_verify_connection_logger_debug(self):
        with patch.object(self.base_model.logger, 'debug') as logger_debug_mock:
            self.base_model.verify_connection()
            logger_debug_mock.assert_called_once_with("Connection verified", method=self.base_model.verify_connection.__name__)

    def test_verify_connection_logger_error(self):
        self.driver_mock.verify_connectivity.side_effect = Exception("Connection error")
        with patch.object(self.base_model.logger, 'error') as logger_error_mock:
            with pytest.raises(Exception):
                self.base_model.verify_connection()
            logger_error_mock.assert_called_once_with("Connection failed", method=self.base_model.verify_connection.__name__, error="Connection error")

    def test_verify_connection_invalid_driver(self):
        invalid_driver = {}
        base_model_invalid = BaseModel(invalid_driver)
        with pytest.raises(AttributeError):
            base_model_invalid.verify_connection()