from unittest.mock import MagicMock, patch

import pytest
from neo4j import Driver

from services.services_layer.src.services_layer.models.arxiv_record import ArxivRecord


class TestArxivRecord:

    IDENTIFIER = "oai:arXiv.org:1906.11285"
    TITLE = "Re-ranking Based Diversification: A Unifying View"
    DATE = "2019-06-26"
    UUID = "1234-5678-9012-3456"
    CREATED = "2021-01-01T00:00:00"
    LAST_MODIFIED = "2021-01-01T00:00:00"

    SINGLE_CREATE_RECORDS_RETURN = MagicMock(
        data=lambda: {
            "a": {
                "arxiv_id": TestArxivRecord.IDENTIFIER,
                "title": TestArxivRecord.TITLE,
                "date": TestArxivRecord.DATE,
                "uuid": TestArxivRecord.UUID,
                "created": TestArxivRecord.CREATED,
                "last_modified": TestArxivRecord.LAST_MODIFIED,
            }
        }
    )

    @pytest.fixture
    def _arxiv_id(self):
        return TestArxivRecord.IDENTIFIER

    @pytest.fixture
    def _created(self):
        return TestArxivRecord.CREATED

    @pytest.fixture
    def _date(self):
        return TestArxivRecord.DATE

    @pytest.fixture
    def driver(self):
        driver = MagicMock(spec=Driver)
        driver.verify_connectivity = MagicMock()
        return driver

    @pytest.fixture
    def _last_modified(self):
        return TestArxivRecord.LAST_MODIFIED

    @pytest.fixture
    def _title(self):
        return TestArxivRecord.TITLE

    @pytest.fixture
    def _uuid(self):
        return TestArxivRecord.UUID

    def test_init_should_succeed_with_valid_params(
        self,
        driver,
        _arxiv_id,
    ):
        arxiv_record = ArxivRecord(driver, _arxiv_id)
        assert arxiv_record.driver == driver
        assert arxiv_record.arxiv_id == _arxiv_id
        assert arxiv_record.title == ""
        assert arxiv_record.date == ""
        assert arxiv_record.uuid is None
        assert arxiv_record.created is None
        assert arxiv_record.last_modified is None

    @pytest.mark.parametrize(
        "d, a",
        [
            (None, "oai:arXiv.org:1906.11285"),
            (123, "oai:arXiv.org:1906.11285"),
            (MagicMock(), None),
            (MagicMock(), 123),
        ],
    )
    def test_init_should_raise_exception_with_invalid_params(self, d, a):
        with pytest.raises(ValueError):
            ArxivRecord(d, a)

    @patch("services.services_layer.src.services_layer.models.arxiv_record.uuid")
    def test_create_should_succeed_with_valid_params(
        self,
        mock_uuid,
        driver,
        _arxiv_id,
        _uuid,
        _title,
        _date,
        _created,
        _last_modified,
    ):
        mock_uuid.uuid4 = MagicMock(return_value=_uuid)
        driver.execute_query.return_value = (
            [
                MagicMock(
                    data=lambda: {
                        "a": {
                            "arxiv_id": _arxiv_id,
                            "title": _title,
                            "date": _date,
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
        arxiv_record = ArxivRecord(driver, _arxiv_id)
        arxiv_record.title = _title
        arxiv_record.date = _date
        arxiv_record.create()
        driver.execute_query.assert_called_once()
        assert arxiv_record.arxiv_id == _arxiv_id
        assert arxiv_record.title == _title
        assert arxiv_record.date == _date
        assert arxiv_record.uuid == _uuid
        assert arxiv_record.created == _created
        assert arxiv_record.last_modified == _last_modified
        print(arxiv_record.created)

    @pytest.mark.parametrize(
        "d, a, t, da",
        [
            (None, "oai:arXiv.org:1906.11285", "Cool Science Paper", "2021-01-01"),
            (123, "oai:arXiv.org:1906.11285", "Cool Science Paper", "2021-01-01"),
            (MagicMock(), None, "Cool Science Paper", "2021-01-01"),
            (MagicMock(), 123, "Cool Science Paper", "2021-01-01"),
            (MagicMock(), "oai:arXiv.org:1906.11285", None, "2021-01-01"),
            (MagicMock(), "oai:arXiv.org:1906.11285", 123, "2021-01-01"),
            (MagicMock(), "oai:arXiv.org:1906.11285", "Cool Science Paper", None),
            (MagicMock(), "oai:arXiv.org:1906.11285", "Cool Science Paper", 123),
        ],
    )
    def test_create_should_raise_exception_with_invalid_params(self, d, a, t, da, driver, _arxiv_id):
        arxiv_record = ArxivRecord(driver, _arxiv_id)
        with pytest.raises(ValueError):
            arxiv_record.arxiv_id = a
            arxiv_record.title = t
            arxiv_record.date = da
            arxiv_record.create()

    def test_create_should_raise_exception_when_no_records_returned(self, driver, _arxiv_id, _title, _date):
        driver.execute_query.return_value = ([], MagicMock(counters=MagicMock(nodes_created=0)), [])
        arxiv_record = ArxivRecord(driver, _arxiv_id)
        arxiv_record.title = _title
        arxiv_record.date = _date
        with pytest.raises(RuntimeError):
            arxiv_record.create()
        driver.execute_query.assert_called_once()

    def test_create_should_not_duplicate_ArxivRecord(self, driver, _arxiv_id, _title, _date):
        driver.execute_query.return_value = (
            [self.SINGLE_CREATE_RECORDS_RETURN],
            MagicMock(counters=MagicMock(nodes_created=0)),
            ["a"],
        )
        title = "C0mput3r Sc13nc3"
        arxiv_record = ArxivRecord(driver, _arxiv_id)
        arxiv_record.title = title
        arxiv_record.date = _date
        arxiv_record.create()
        driver.execute_query.assert_called_once()
        assert arxiv_record.title == _title

    def test_create_should_raise_exception_if_record_improperly_created(
        self, driver, _arxiv_id, _title, _date, _uuid, _created, _last_modified
    ):
        driver.execute_query.return_value = (
            [
                MagicMock(
                    data=lambda: {
                        "a": {
                            "arxiv_id": _arxiv_id,
                            "title": _title,
                            "date": _date,
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
        arxiv_record = ArxivRecord(driver, _arxiv_id)
        arxiv_record.title = _title
        arxiv_record.date = _date
        with pytest.raises(ValueError):
            arxiv_record.create()
        driver.execute_query.assert_called_once()
        driver.reset_mock()
        driver.execute_query.return_value = (
            [
                MagicMock(
                    data=lambda: {
                        "a": {
                            "arxiv_id": _arxiv_id,
                            "title": _title,
                            "date": _date,
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
            arxiv_record.create()
        driver.execute_query.assert_called_once()
        driver.reset_mock()
        driver.execute_query.return_value = (
            [
                MagicMock(
                    data=lambda: {
                        "a": {
                            "arxiv_id": _arxiv_id,
                            "title": _title,
                            "date": _date,
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
            arxiv_record.create()
        driver.execute_query.assert_called_once()

    def test_load_should_succeed_if_record_exists(
        self,
        driver,
        _arxiv_id,
        _title,
        _date,
        _uuid,
        _created,
        _last_modified,
    ):
        driver.execute_query.return_value = (
            [self.SINGLE_CREATE_RECORDS_RETURN],
            MagicMock(counters=MagicMock(nodes_created=1)),
            ["a"],
        )
        arxiv_record = ArxivRecord(driver, _arxiv_id)
        assert arxiv_record.load()
        assert "MATCH (a:ArxivRecord {arxiv_id: $arxiv_id}) RETURN a" in driver.execute_query.call_args[0]
        assert arxiv_record.arxiv_id == _arxiv_id
        assert arxiv_record.title == _title
        assert arxiv_record.date == _date
        assert arxiv_record.uuid == _uuid
        assert arxiv_record.created == _created
        assert arxiv_record.last_modified == _last_modified

    def test_load_should_return_false_if_record_does_not_exist(self, driver, _arxiv_id):
        driver.execute_query.return_value = ([], MagicMock(counters=MagicMock(nodes_created=0)), [])
        arxiv_record = ArxivRecord(driver, _arxiv_id)
        assert not arxiv_record.load()
        assert "MATCH (a:ArxivRecord {arxiv_id: $arxiv_id}) RETURN a" in driver.execute_query.call_args[0]
        assert arxiv_record.arxiv_id == _arxiv_id
        assert arxiv_record.title == ""
        assert arxiv_record.date == ""
        assert arxiv_record.uuid is None
        assert arxiv_record.created is None
        assert arxiv_record.last_modified is None

    def test_load_should_raise_exception_if_invalid_code(self, driver, _arxiv_id):
        arxiv_record = ArxivRecord(driver, _arxiv_id)
        arxiv_record.arxiv_id = None
        with pytest.raises(ValueError):
            arxiv_record.load()
        arxiv_record.arxiv_id = 123
        with pytest.raises(ValueError):
            arxiv_record.load()

    def test_load_should_raise_exception_if_driver_not_connected(self, driver, _arxiv_id):
        driver.verify_connectivity.side_effect = Exception("Connection error")
        arxiv_record = ArxivRecord(driver, _arxiv_id)
        with pytest.raises(Exception):
            arxiv_record.load()
        driver.verify_connectivity.assert_called_once()

    @pytest.mark.parametrize(
        "query",
        [
            (
                MagicMock(
                    data=lambda: {
                        "a": {
                            "arxiv_id": "",
                            "title": "Cool Science Paper",
                            "date": "2021-01-01",
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
                            "arxiv_id": "oai:arXiv.org:1906.11285",
                            "title": "Cool Science Paper",
                            "date": "",
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
                            "arxiv_id": "oai:arXiv.org:1906.11285",
                            "title": "Cool Science Paper",
                            "date": "2021-01-01",
                            "uuid": "",
                            "created": "2021-01-01T00:00:00",
                            "last_modified": "2021-01-01T00:00:00",
                        }
                    }
                )
            ),
        ],
    )
    def test_load_should_raise_exception_if_returned_values_not_valid(self, query, driver, _arxiv_id):
        driver.execute_query.return_value = (
            [query],
            MagicMock(counters=MagicMock(nodes_created=1)),
            ["a"],
        )
        arxiv_record = ArxivRecord(driver, _arxiv_id)
        with pytest.raises(ValueError):
            arxiv_record.load()
        driver.execute_query.assert_called_once()
        driver.reset_mock()

    def test_find_should_return_arxiv_record(self, driver, _arxiv_id, _title, _date, _uuid, _created, _last_modified):
        driver.execute_query.return_value = (
            [self.SINGLE_CREATE_RECORDS_RETURN],
            MagicMock(counters=MagicMock(nodes_created=1)),
            ["a"],
        )
        arxiv_record = ArxivRecord.find(driver, _arxiv_id)
        driver.execute_query.assert_called_once()
        assert arxiv_record.arxiv_id == _arxiv_id
        assert arxiv_record.title == _title
        assert arxiv_record.date == _date
        assert arxiv_record.uuid == _uuid
        assert arxiv_record.created == _created
        assert arxiv_record.last_modified == _last_modified

    def test_find_should_return_none_if_no_record(self, driver, _arxiv_id):
        driver.execute_query.return_value = (
            [MagicMock(data=lambda: {})],
            MagicMock(counters=MagicMock(nodes_created=0)),
            [],
        )
        arxiv_record = ArxivRecord.find(driver, _arxiv_id)
        driver.execute_query.assert_called_once()
        assert arxiv_record is None

    @pytest.mark.parametrize(
        "d, i",
        [
            (None, "oai:arXiv.org:1906.11285"),
            (123, "oai:arXiv.org:1906.11285"),
            (MagicMock(), None),
            (MagicMock(), 123),
        ],
    )
    def test_find_should_raise_exception_if_invalid_params(self, d, i):
        with pytest.raises(ValueError):
            ArxivRecord.find(d, i)

    def test_find_should_raise_exception_if_driver_not_connected(self, driver, _arxiv_id):
        driver.verify_connectivity.side_effect = Exception("Connection error")
        with pytest.raises(Exception):
            ArxivRecord.find(driver, _arxiv_id)
        driver.verify_connectivity.assert_called_once()

    def test_find_all_should_throw_not_implemented_error(self, driver, _arxiv_id):
        with pytest.raises(NotImplementedError):
            ArxivRecord.find_all(driver)
