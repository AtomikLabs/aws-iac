from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from neo4j import Driver

from orchestration.airflow.dags.shared.models.abstract import Abstract
from orchestration.airflow.dags.shared.utils.constants import S3_KEY_DATE_FORMAT


class TestAbstract:

    URL = "https://arxiv.org/abs/1906.11285"
    BUCKET = "test-bucket"
    KEY = "s3://test-bucket/test-key"
    DATE = "2019-06-26"
    UUID = "1234-5678-9012-3456"
    CREATED = datetime.strptime("2021-01-01T00-00-00", S3_KEY_DATE_FORMAT)
    LAST_MODIFIED = datetime.strptime("2021-01-01T00-00-00", S3_KEY_DATE_FORMAT)

    SINGLE_CREATE_RECORDS_RETURN = MagicMock(
        data=lambda: {
            "a": {
                "url": TestAbstract.URL,
                "bucket": TestAbstract.BUCKET,
                "key": TestAbstract.KEY,
                "uuid": TestAbstract.UUID,
                "created": TestAbstract.CREATED,
                "last_modified": TestAbstract.LAST_MODIFIED,
            }
        }
    )

    @pytest.fixture
    def _created(self):
        return TestAbstract.CREATED

    @pytest.fixture
    def driver(self):
        driver = MagicMock(spec=Driver)
        driver.verify_connectivity = MagicMock()
        return driver

    @pytest.fixture
    def _url(self):
        return TestAbstract.URL

    @pytest.fixture
    def _last_modified(self):
        return TestAbstract.LAST_MODIFIED

    @pytest.fixture
    def _bucket(self):
        return TestAbstract.BUCKET

    @pytest.fixture
    def _key(self):
        return TestAbstract.KEY

    @pytest.fixture
    def _uuid(self):
        return TestAbstract.UUID

    def test_init_should_succeed_with_valid_params(self, driver, _url, _bucket, _key):
        abstract = Abstract(driver, _url, _bucket, _key)
        assert abstract.driver == driver
        assert abstract.url == _url
        assert abstract.bucket == _bucket
        assert abstract.key == _key
        assert abstract.uuid is None
        assert abstract.created is None
        assert abstract.last_modified is None

    @pytest.mark.parametrize(
        "d, u, b, k",
        [
            (None, "https://arxiv.org/abs/1906.11285", "This is a test abstract", "s3://test-bucket/test-key"),
            (123, "https://arxiv.org/abs/1906.11285", "This is a test abstract", "s3://test-bucket/test-key"),
            (MagicMock(spec=Driver), 123, "This is a test abstract", "s3://test-bucket/test-key"),
            (MagicMock(spec=Driver), "https://arxiv.org/abs/1906.11285", 123, "s3://test-bucket/test-key"),
            (MagicMock(spec=Driver), "https://arxiv.org/abs/1906.11285", "This is a test abstract", 123),
        ],
    )
    def test_init_should_raise_exception_with_invalid_params(self, d, u, b, k):
        with pytest.raises(ValueError):
            Abstract(d, u, b, k)

    @patch("orchestration.airflow.dags.shared.models.abstract.uuid")
    def test_create_should_succeed_with_valid_params(
        self,
        mock_uuid,
        driver,
        _url,
        _bucket,
        _key,
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
                            "bucket": _bucket,
                            "key": _key,
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
        abstract = Abstract(driver, _url, _bucket, _key)
        abstract.create()
        driver.execute_query.assert_called_once()
        assert abstract.url == _url
        assert abstract.bucket == _bucket
        assert abstract.key == _key
        assert abstract.uuid == _uuid
        assert abstract.created == _created
        assert abstract.last_modified == _last_modified

    @pytest.mark.parametrize(
        "d, u, b, k",
        [
            (None, "https://arxiv.org/abs/1906.11285", "This is a test abstract", "s3://test-bucket/test-key"),
            (123, "https://arxiv.org/abs/1906.11285", "This is a test abstract", "s3://test-bucket/test-key"),
            (MagicMock(spec=Driver), 123, "This is a test abstract", "s3://test-bucket/test-key"),
            (MagicMock(spec=Driver), "https://arxiv.org/abs/1906.11285", 123, "s3://test-bucket/test-key"),
            (MagicMock(spec=Driver), "https://arxiv.org/abs/1906.11285", "This is a test abstract", 123),
        ],
    )
    def test_create_should_raise_exception_with_invalid_params(self, d, u, b, k, driver, _url):
        abstract = Abstract(driver, _url)
        abstract.url = u
        abstract.bucket = b
        abstract.key = k
        if not isinstance(d, Driver):
            with pytest.raises(AttributeError):
                abstract.driver = d
                abstract.create()
        else:
            with pytest.raises(ValueError):
                abstract.create()

    def test_create_should_raise_exception_when_no_records_returned(self, driver, _url, _bucket, _key):
        driver.execute_query.return_value = ([], MagicMock(counters=MagicMock(nodes_created=0)), [])
        abstract = Abstract(driver, _url, _bucket, _key)
        with pytest.raises(RuntimeError):
            abstract.create()
        driver.execute_query.assert_called_once()

    def test_create_should_not_duplicate_Abstract(self, driver, _url, _bucket, _key):
        driver.execute_query.return_value = (
            [self.SINGLE_CREATE_RECORDS_RETURN],
            MagicMock(counters=MagicMock(nodes_created=0)),
            ["a"],
        )
        text = "A Møøse once bit my sister... No realli!"
        abstract = Abstract(driver, _url, _bucket, _key)
        abstract.bucket = text
        abstract.create()
        driver.execute_query.assert_called_once()
        assert abstract.bucket == _bucket

    def test_create_should_raise_exception_if_record_improperly_created(
        self, driver, _url, _bucket, _key, _uuid, _created, _last_modified
    ):
        driver.execute_query.return_value = (
            [
                MagicMock(
                    data=lambda: {
                        "a": {
                            "url": _url,
                            "bucket": _bucket,
                            "storage_url": _key,
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
        abstract = Abstract(driver, _url, _bucket, _key)
        with pytest.raises(ValueError):
            abstract.create()
        driver.execute_query.assert_called_once()
        driver.reset_mock()
        driver.execute_query.return_value = (
            [
                MagicMock(
                    data=lambda: {
                        "a": {
                            "url": _url,
                            "bucket": _bucket,
                            "key": _key,
                            "uuid": _uuid,
                            "created": None,
                            "last_modified": _last_modified,
                        }
                    }
                )
            ],
            MagicMock(counters=MagicMock(nodes_created=1)),
            ["a"],
        )
        with pytest.raises(ValueError):
            abstract.create()
        driver.execute_query.assert_called_once()
        driver.reset_mock()
        driver.execute_query.return_value = (
            [
                MagicMock(
                    data=lambda: {
                        "a": {
                            "url": _url,
                            "bucket": _bucket,
                            "key": _key,
                            "uuid": _uuid,
                            "created": _created,
                            "last_modified": None,
                        }
                    }
                )
            ],
            MagicMock(counters=MagicMock(nodes_created=1)),
            ["a"],
        )
        with pytest.raises(ValueError):
            abstract.create()
        driver.execute_query.assert_called_once()

    def test_load_should_succeed_if_record_exists(
        self,
        driver,
        _url,
        _bucket,
        _key,
        _uuid,
        _created,
        _last_modified,
    ):
        driver.execute_query.return_value = (
            [self.SINGLE_CREATE_RECORDS_RETURN],
            MagicMock(counters=MagicMock(nodes_created=1)),
            ["a"],
        )
        abstract = Abstract(driver, _url)
        assert abstract.load()
        assert "MATCH (a:Abstract {url: $url}) RETURN a" in driver.execute_query.call_args[0]
        assert abstract.url == _url
        assert abstract.bucket == _bucket
        assert abstract.key == _key
        assert abstract.uuid == _uuid
        assert abstract.created == _created
        assert abstract.last_modified == _last_modified

    def test_load_should_return_false_if_record_does_not_exist(self, driver, _url):
        driver.execute_query.return_value = ([], MagicMock(counters=MagicMock(nodes_created=0)), [])
        abstract = Abstract(driver, _url)
        assert not abstract.load()
        assert "MATCH (a:Abstract {url: $url}) RETURN a" in driver.execute_query.call_args[0]
        assert abstract.url == _url
        assert abstract.bucket == ""
        assert abstract.key == ""
        assert abstract.uuid is None
        assert abstract.created is None
        assert abstract.last_modified is None

    def test_load_should_raise_exception_if_invalid_url(self, driver, _url):
        abstract = Abstract(driver, _url)
        abstract.url = None
        with pytest.raises(ValueError):
            abstract.load()
        abstract.url = 123
        with pytest.raises(ValueError):
            abstract.load()

    def test_load_should_raise_exception_if_driver_not_connected(self, driver, _url):
        driver.verify_connectivity.side_effect = Exception("Connection error")
        abstract = Abstract(driver, _url)
        with pytest.raises(Exception):
            abstract.load()
        driver.verify_connectivity.assert_called_once()

    @pytest.mark.parametrize(
        "query",
        [
            (
                MagicMock(
                    data=lambda: {
                        "a": {
                            "url": "",
                            "text": "This is a test abstract",
                            "storage_url": "s3://test-bucket/test-key",
                            "uuid": "1234-5678-9012-3456",
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
                            "url": "",
                            "text": "This is a test abstract",
                            "storage_url": "s3://test-bucket/test-key",
                            "uuid": "1234-5678-9012-3456",
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
                            "url": "",
                            "text": "This is a test abstract",
                            "storage_url": "s3://test-bucket/test-key",
                            "uuid": "1234-5678-9012-3456",
                            "created": datetime.strptime("2021-01-01T00-00-00", S3_KEY_DATE_FORMAT),
                            "last_modified": datetime.strptime("2021-01-01T00-00-00", S3_KEY_DATE_FORMAT),
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
        abstract = Abstract(driver, _url)
        with pytest.raises(ValueError):
            abstract.load()
        driver.execute_query.assert_called_once()
        driver.reset_mock()

    def test_find_should_return_abstract(self, driver, _url, _bucket, _key, _uuid, _created, _last_modified):
        driver.execute_query.return_value = (
            [self.SINGLE_CREATE_RECORDS_RETURN],
            MagicMock(counters=MagicMock(nodes_created=1)),
            ["a"],
        )
        abstract = Abstract.find(driver, _url)
        driver.execute_query.assert_called_once()
        assert abstract.url == _url
        assert abstract.bucket == _bucket
        assert abstract.key == _key
        assert abstract.uuid == _uuid
        assert abstract.created == _created
        assert abstract.last_modified == _last_modified

    def test_find_should_return_none_if_no_record(self, driver, _url):
        driver.execute_query.return_value = (
            [MagicMock(data=lambda: {})],
            MagicMock(counters=MagicMock(nodes_created=0)),
            [],
        )
        abstract = Abstract.find(driver, _url)
        driver.execute_query.assert_called_once()
        assert abstract is None

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
            Abstract.find(d, u)

    def test_find_should_raise_exception_if_driver_not_connected(self, driver, _url):
        driver.verify_connectivity.side_effect = Exception("Connection error")
        with pytest.raises(Exception):
            Abstract.find(driver, _url)
        driver.verify_connectivity.assert_called_once()

    def test_find_all_should_should_turn_all_found_records(
        self, driver, _url, _bucket, _key, _uuid, _created, _last_modified
    ):
        driver.execute_query.return_value = (
            [self.SINGLE_CREATE_RECORDS_RETURN, self.SINGLE_CREATE_RECORDS_RETURN],
            MagicMock(counters=MagicMock()),
            ["a", "a"],
        )
        abstracts = Abstract.find_all(driver)
        driver.execute_query.assert_called_once()
        assert len(abstracts) == 2
        for abstract in abstracts:
            assert abstract.url == _url
            assert abstract.bucket == _bucket
            assert abstract.key == _key
            assert abstract.uuid == _uuid
            assert abstract.created == _created
            assert abstract.last_modified == _last_modified
