import uuid

import structlog
from constants import FAILED_TO_CREATE_ABSTRACT, S3_KEY_DATE_FORMAT
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


class Abstract(BaseModel):

    LABEL = "Abstract"

    def __init__(self, driver: Driver = None, url: str = "", text: str = "", storage_url: str = ""):
        super().__init__(driver)
        if url and not validate_strings(url):
            message = "URL must be a valid string if provided"
            self.logger.error(message, method=self.__init__.__name__)
            raise ValueError(message)
        if text and not validate_strings(text):
            message = "Text must be a valid string if provided"
            self.logger.error(message, method=self.__init__.__name__)
            raise ValueError(message)
        if storage_url and not validate_strings(storage_url):
            message = "Storage URL must be a valid string if provided"
            self.logger.error(message, method=self.__init__.__name__)
            raise ValueError(message)
        self.text = text
        self.storage_url = storage_url
        self.url = url
        self.uuid = None
        self.created = None
        self.last_modified = None

    def create(self, url: str = "", text: str = "", storage_url: str = ""):
        if not validate_strings(self.text, self.url) and not validate_strings(text, url):
            message = "Invalid text, storage url, or url"
            self.logger.error(message, method=self.create.__name__)
            raise ValueError(message)
        try:
            self.text = text if validate_strings(text) else self.text
            self.storage_url = storage_url if validate_strings(storage_url) else self.storage_url
            self.url = url if validate_strings(url) else self.url
            self.verify_connection()
            self.logger.debug(
                "Creating Abstract",
                method=self.create.__name__,
                text=self.text,
                storage_url=self.storage_url,
                url=self.url,
            )
            now = get_storage_key_datetime()
            properties = {
                "text": self.text,
                "uuid": str(uuid.uuid4()),
                "storage_url": self.storage_url,
                "url": self.url,
                "created": now,
                "last_modified": now,
            }
            records, summary, _ = self.driver.execute_query(
                """
                MERGE (a:Abstract {url: $url})
                ON CREATE SET a += $props
                RETURN a""",
                url=self.url,
                props=properties,
                database_=self.db,
            )
            if records and summary.counters.nodes_created == 1:
                self.logger.debug(
                    "Abstract created", method=self.create.__name__, code=self.text, name=self.storage_url
                )
            elif records and summary.counters.nodes_created == 0:
                self.logger.debug(
                    "Abstract already exists", method=self.create.__name__, code=self.text, name=self.storage_url
                )
            else:
                self.logger.error(
                    FAILED_TO_CREATE_ABSTRACT, method=self.create.__name__, code=self.text, name=self.storage_url
                )
                raise RuntimeError()
            data = records[0].data().get("a", {})
            self.text = data.get("text", "")
            self.url = data.get("url", "")
            self.storage_url = data.get("storage_url", "")
            self.uuid = data.get("uuid", "")
            self.created = data.get("created", None)
            self.last_modified = data.get("last_modified", None)
            if not validate_strings(self.uuid) or self.created is None or self.last_modified is None:
                self.logger.error(
                    "Failed to properly create Abstract",
                    method=self.create.__name__,
                    text=self.text,
                    storage_url=self.storage_url,
                    url=self.url,
                    uuid=self.uuid,
                    created=self.created,
                    last_modified=self.last_modified,
                )
                raise ValueError("Failed to create Abstract")
        except Exception as e:
            self.logger.error("Error while creating Abstract", method=self.create.__name__, error=str(e))
            raise e

    @classmethod
    def find(cls, driver: Driver, url: str):
        if not driver or not isinstance(driver, Driver):
            raise ValueError("Invalid driver")
        if not validate_strings(url):
            raise ValueError("Invalid url")
        try:
            driver.verify_connectivity()
            records, _, _ = driver.execute_query(
                f"MATCH (a:{Abstract.LABEL} {{url: $url}}) RETURN a", url=url, database_="neo4j"
            )
            if records and records[0] and records[0].data():
                data = records[0].data().get("a", {})
                print(data)
                abstract = Abstract(
                    driver=driver,
                    url=data.get("url", ""),
                    text=data.get("text", ""),
                    storage_url=data.get("storage_url", ""),
                )
                abstract.uuid = data.get("uuid", "")
                abstract.created = data.get("created", None)
                abstract.last_modified = data.get("last_modified", None)
                if not validate_strings(
                    abstract.text,
                    abstract.storage_url,
                    abstract.url,
                    abstract.uuid,
                ) or abstract.created is None or abstract.last_modified is None:
                    raise ValueError("Failed to load Abstract")
                return abstract
            return None
        except Exception as e:
            raise e

    @classmethod
    def find_all(cls, driver: Driver):
        try:
            driver.verify_connectivity()
            records, _, _ = driver.execute_query(f"MATCH (a:{Abstract.LABEL}) RETURN a", database_="neo4j")
            if records:
                abstracts = []
                for record in records:
                    data = record.data().get("a", {})
                    abstract = Abstract(
                        driver=driver,
                        url=data.get("url", ""),
                        text=data.get("text", ""),
                        storage_url=data.get("storage_url", ""),
                    )
                    abstract.uuid = data.get("uuid")
                    abstract.created = data.get("created")
                    abstract.last_modified = data.get("last_modified")
                    if not validate_strings(
                        abstract.text,
                        abstract.storage_url,
                        abstract.url,
                        abstract.uuid,
                    ) or abstract.created is None or abstract.last_modified is None:
                        raise ValueError("Failed to load Abstract")
                    abstracts.append(abstract)
                return abstracts
        except Exception as e:
            raise e

    def load(self) -> bool:
        if not validate_strings(self.url):
            self.logger.error(
                "Invalid url", method=self.load.__name__, text=self.text, storage_url=self.storage_url, url=self.url
            )
            raise ValueError("Invalid url")
        try:
            self.verify_connection()
            self.logger.debug(
                "Loading Abstract",
                method=self.load.__name__,
                text=self.text,
                storage_url=self.storage_url,
                url=self.url,
            )
            records, _, _ = self.driver.execute_query(
                f"MATCH (a:{self.LABEL} {{url: $url}}) RETURN a", url=self.url, database_=self.db
            )
            if records:
                self.logger.debug(
                    "Abstract loaded",
                    method=self.load.__name__,
                    text=self.text,
                    storage_url=self.storage_url,
                    url=self.url,
                )
                data = records[0].data().get("a", {})
                self.text = data.get("text", "")
                self.storage_url = data.get("storage_url", "")
                self.url = data.get("url", "")
                self.uuid = data.get("uuid", "")
                self.created = data.get("created", None)
                self.last_modified = data.get("last_modified", None)
                if not validate_strings(
                    self.text, self.storage_url, self.url, self.uuid
                ) or self.created is None or self.last_modified is None:
                    self.logger.error(
                        "Failed to properly load Abstract",
                        method=self.load.__name__,
                        text=self.text,
                        storage_url=self.storage_url,
                        url=self.url,
                        uuid=self.uuid,
                        created=self.created,
                        last_modified=self.last_modified,
                    )
                    raise ValueError("Failed to load Abstract")
            return True if records else False
        except Exception as e:
            self.logger.error(
                "Failed to load Abstract",
                method=self.load.__name__,
                error=str(e),
                text=self.text,
                storage_url=self.storage_url,
                url=self.url,
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
        super()._relate(driver, label, start_label, start_uuid, end_label, end_uuid, True)