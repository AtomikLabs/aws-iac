import uuid

import structlog
from constants import FAILED_TO_CREATE_ARXIV_RECORD, S3_KEY_DATE_FORMAT
from models.base_model import BaseModel
from neo4j import Driver
from utils import get_storage_key_datetime, validate_strings

structlog.configure(
    [
        structlog.stdlib.filter_by_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.dict_tracebacks,
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)


class ArxivRecord(BaseModel):

    LABEL = "ArxivRecord"

    def __init__(self, driver: Driver = None, arxiv_id: str = "", title: str = "", date: str = ""):
        super().__init__(driver)
        self.arxiv_id = arxiv_id
        self.uuid = None
        self.title = title
        self.date = date
        self.created = None
        self.last_modified = None

    def create(self, arxiv_id: str = ""):
        if not validate_strings(self.arxiv_id, self.title, self.date):
            message = "Invalid arxiv_id, title, or date"
            self.logger.error(
                message, method=self.create.__name__, arxiv_id=self.arxiv_id, title=self.title, date=self.date
            )
            raise ValueError(message)
        try:
            self.arxiv_id = self.arxiv_id if self.arxiv_id else arxiv_id
            self.verify_connection()
            self.logger.debug("Creating ArxivRecord", method=self.create.__name__, arxiv_id=self.arxiv_id)
            now = get_storage_key_datetime().strftime(S3_KEY_DATE_FORMAT)
            properties = {
                "arxiv_id": self.arxiv_id,
                "uuid": str(uuid.uuid4()),
                "title": self.title,
                "date": self.date,
                "created": now,
                "last_modified": now,
            }
            print(properties)
            records, summary, _ = self.driver.execute_query(
                """
                MERGE (a:ArxivRecord {arxiv_id: $arxiv_id})
                ON CREATE SET a += $props
                RETURN a""",
                arxiv_id=self.arxiv_id,
                props=properties,
                database_=self.db,
            )
            if records and summary.counters.nodes_created == 1:
                self.logger.debug("ArxivRecord created", method=self.create.__name__, arxiv_id=self.arxiv_id)
            elif records and summary.counters.nodes_created == 0:
                self.logger.debug("ArxivRecord already exists", method=self.create.__name__, arxiv_id=self.arxiv_id)
            else:
                self.logger.error(FAILED_TO_CREATE_ARXIV_RECORD, method=self.create.__name__, arxiv_id=self.arxiv_id)
                raise RuntimeError()
            print("Records: ", records[0].data())
            data = records[0].data().get("a", {})
            self.arxiv_id = data.get("arxiv_id", "")
            self.title = data.get("title", "")
            self.date = data.get("date", "")
            self.uuid = data.get("uuid", "")
            self.created = data.get("created", "").strftime(S3_KEY_DATE_FORMAT)
            self.last_modified = data.get("last_modified", "").strftime(S3_KEY_DATE_FORMAT)

            if not validate_strings(self.arxiv_id, self.title, self.date, self.uuid, self.created, self.last_modified):
                self.logger.error(
                    "Failed to properly create ArxivRecord",
                    method=self.create.__name__,
                    arxiv_id=self.arxiv_id,
                    title=self.title,
                    date=self.date,
                    uuid=self.uuid,
                    created=self.created,
                    last_modified=self.last_modified,
                )
                raise ValueError("Failed to create ArxivRecord")
        except Exception as e:
            self.logger.error("Error while creating ArxivRecord", method=self.create.__name__, error=str(e))
            raise e

    @classmethod
    def find(cls, driver: Driver, arxiv_id: str):
        if not driver or not isinstance(driver, Driver):
            raise ValueError("Invalid driver")
        if not validate_strings(arxiv_id):
            raise ValueError("Invalid arxiv_id")
        try:
            driver.verify_connectivity()
            records, _, _ = driver.execute_query(
                f"MATCH (a:{ArxivRecord.LABEL} {{arxiv_id: $arxiv_id}}) RETURN a", arxiv_id=arxiv_id, database_="neo4j"
            )
            if records and records[0] and records[0].data():
                data = records[0].data().get("a", {})
                arxiv_record = ArxivRecord(driver=driver, arxiv_id=data.get("arxiv_id", ""))
                arxiv_record.uuid = data.get("uuid", "")
                arxiv_record.title = data.get("title", "")
                arxiv_record.date = data.get("date", "")
                arxiv_record.created = data.get("created", "").strftime(S3_KEY_DATE_FORMAT)
                arxiv_record.last_modified = data.get("last_modified", "").strftime(S3_KEY_DATE_FORMAT)
                if not validate_strings(
                    arxiv_record.arxiv_id,
                    arxiv_record.title,
                    arxiv_record.uuid,
                    arxiv_record.date,
                    arxiv_record.created,
                    arxiv_record.last_modified,
                ):
                    raise ValueError("Failed to load ArxivRecord")
                return arxiv_record
            return None
        except Exception as e:
            raise e

    @classmethod
    def find_all(cls, driver: Driver):
        raise NotImplementedError()  # each record should be unique

    def load(self) -> bool:
        if not validate_strings(self.arxiv_id):
            self.logger.error("Invalid arxiv_id", method=self.load.__name__, arxiv_id=self.arxiv_id)
            raise ValueError("Invalid arxiv_id")
        try:
            self.verify_connection()
            self.logger.debug("Loading ArxivRecord", method=self.load.__name__, arxiv_id=self.arxiv_id)
            records, _, _ = self.driver.execute_query(
                f"MATCH (a:{ArxivRecord.LABEL} {{arxiv_id: $arxiv_id}}) RETURN a",
                arxiv_id=self.arxiv_id,
                database_=self.db,
            )
            if records:
                self.logger.debug("ArxivRecord loaded", method=self.load.__name__, arxiv_id=self.arxiv_id)
                data = records[0].data().get("a", {})
                self.arxiv_id = data.get("arxiv_id", "")
                self.title = data.get("title", "")
                self.date = data.get("date", "")
                self.uuid = data.get("uuid", "")
                self.created = data.get("created", "").strftime(S3_KEY_DATE_FORMAT)
                self.last_modified = data.get("last_modified", "").strftime(S3_KEY_DATE_FORMAT)
                if not validate_strings(
                    self.arxiv_id, self.title, self.date, self.uuid, self.created, self.last_modified
                ):
                    self.logger.error(
                        "Failed to properly load ArxivRecord",
                        method=self.load.__name__,
                        arxiv_id=self.arxiv_id,
                        title=self.title,
                        date=self.date,
                        uuid=self.uuid,
                        created=self.created,
                        last_modified=self.last_modified,
                    )
                    raise ValueError("Failed to load ArxivRecord")
            return True if records else False
        except Exception as e:
            self.logger.error(
                "Failed to load ArxivRecord", method=self.load.__name__, error=str(e), arxiv_id=self.arxiv_id
            )
            raise e

    def relate(
        self,
        driver: Driver,
        label: str,
        start_label: str,
        start_uuid: str,
        end_label: str,
        end_uuid: str,
        unique: bool = True,
        properties: dict = None,
    ):
        super()._relate(driver, label, start_label, start_uuid, end_label, end_uuid, unique, properties)
