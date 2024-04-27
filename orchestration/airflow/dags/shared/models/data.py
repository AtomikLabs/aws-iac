import logging
import uuid

import structlog
from dags.shared.models.base_model import BaseModel
from dags.shared.utils.constants import FAILED_TO_CREATE_DATA
from dags.shared.utils.utils import get_storage_key_datetime, validate_strings
from neo4j import Driver

structlog.configure(
    [
        structlog.stdlib.filter_by_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.dict_tracebacks,
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()
logger.setLevel(logging.INFO)


class Data(BaseModel):

    LABEL = "Data"

    def __init__(
        self, driver: Driver = None, url: str = "", format: str = "", description: str = "", size_bytes: int = 0
    ):
        super().__init__(driver)
        if url != "" and not validate_strings(url):
            self.logger.error("URL must be a valid string if provided", method=self.__init__.__name__)
            raise ValueError("URL must be a valid string if provided")
        if format != "" and not validate_strings(format):
            self.logger.error("Name must be a valid string if provided", method=self.__init__.__name__)
            raise ValueError("Name must be a valid string if provided")
        if description != "" and not validate_strings(description):
            self.logger.error("Description must be a valid string if provided", method=self.__init__.__name__)
            raise ValueError("Description must be a valid string if provided")
        if not isinstance(size_bytes, int) or size_bytes < 0:
            self.logger.error("Size must be a positive integer if provided", method=self.__init__.__name__)
            raise ValueError("Size must be a positive integer if provided")
        self.url = url
        self.format = format
        self.description = description
        self.size_bytes = size_bytes
        self.uuid = None
        self.created = None
        self.last_modified = None

    def create(self, url: str = "", format: str = "", description: str = "", size_bytes: int = 0):
        if not validate_strings(self.url, self.format, self.description) and not validate_strings(
            url, format, description
        ):
            message = "Invalid url, format, or description"
            self.logger.error(message, method=self.create.__name__)
            raise ValueError(message)
        if size_bytes < 0:
            message = "Size must be a positive integer"
            self.logger.error(message, method=self.create.__name__)
            raise ValueError(message)
        try:
            self.url = self.url if validate_strings(self.url) else url
            self.format = format if validate_strings(format) else self.format
            self.description = description if validate_strings(description) else self.description
            self.size_bytes = size_bytes if size_bytes > 0 else self.size_bytes
            self.verify_connection()
            self.logger.debug(
                "Creating Data",
                method=self.create.__name__,
                url=self.url,
                format=self.format,
                description=self.description,
                size_bytes=self.size_bytes,
            )
            now = get_storage_key_datetime()
            properties = {
                "url": self.url,
                "uuid": str(uuid.uuid4()),
                "format": self.format,
                "description": self.description,
                "size_bytes": self.size_bytes,
                "created": now,
                "last_modified": now,
            }
            records, summary, _ = self.driver.execute_query(
                """
                MERGE (a:Data {url: $url})
                ON CREATE SET a += $props
                RETURN a""",
                url=self.url,
                props=properties,
                database_=self.db,
            )
            if records and summary.counters.nodes_created == 1:
                self.logger.debug(
                    "Data created",
                    method=self.create.__name__,
                    url=self.url,
                    format=self.format,
                    description=self.description,
                    size_bytes=self.size_bytes,
                )
            elif records and summary.counters.nodes_created == 0:
                self.logger.debug(
                    "Data already exists",
                    method=self.create.__name__,
                    url=self.url,
                    format=self.format,
                    description=self.description,
                    size_bytes=self.size_bytes,
                )
            else:
                self.logger.error(
                    FAILED_TO_CREATE_DATA,
                    method=self.create.__name__,
                    url=self.url,
                    format=self.format,
                    description=self.description,
                    size_bytes=self.size_bytes,
                )
                raise RuntimeError()
            data = records[0].data().get("a", {})
            self.format = data.get("format", "")
            self.uuid = data.get("uuid", "")
            self.description = data.get("description", "")
            self.size_bytes = data.get("size_bytes", 0)
            self.created = data.get("created", None)
            self.last_modified = data.get("last_modified", None)
            if not validate_strings(self.uuid) or self.created is None or self.last_modified is None or size_bytes < 0:
                self.logger.error(
                    "Failed to properly create Data",
                    method=self.create.__name__,
                    url=self.url,
                    format=self.format,
                    description=self.description,
                    size_bytes=self.size_bytes,
                    uuid=self.uuid,
                    created=self.created,
                    last_modified=self.last_modified,
                )
                raise ValueError("Failed to create Data")
        except Exception as e:
            self.logger.error("Error while creating Data", method=self.create.__name__, error=str(e))
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
                f"MATCH (a:{Data.LABEL} {{url: $url}}) RETURN a", url=url, database_="neo4j"
            )
            if records and records[0] and records[0].data():
                data = records[0].data().get("a", {})
                data_source = Data(
                    driver=driver,
                    url=data.get("url", ""),
                    format=data.get("format", ""),
                    description=data.get("description", ""),
                    size_bytes=data.get("size_bytes", 0),
                )
                data_source.uuid = data.get("uuid", "")
                data_source.created = data.get("created", None)
                data_source.last_modified = data.get("last_modified", None)
                if (
                    not validate_strings(
                        data_source.url,
                        data_source.format,
                        data_source.uuid,
                    )
                    or data_source.created is None
                    or data_source.last_modified is None
                    or data_source.size_bytes < 0
                ):
                    raise ValueError("Failed to load Data")
                return data_source
            return None
        except Exception as e:
            raise e

    @classmethod
    def find_all(cls, driver: Driver):
        try:
            driver.verify_connectivity()
            records, _, _ = driver.execute_query(f"MATCH (a:{Data.LABEL}) RETURN a", database_="neo4j")
            if records:
                data_sources = []
                for record in records:
                    data = record.data().get("a", {})
                    data_source = Data(
                        driver=driver,
                        url=data.get("url"),
                        format=data.get("format"),
                        description=data.get("description"),
                        size_bytes=data.get("size_bytes", 0),
                    )
                    data_source.uuid = data.get("uuid")
                    data_source.created = data.get("created")
                    data_source.last_modified = data.get("last_modified")
                    if (
                        not validate_strings(
                            data_source.url,
                            data_source.format,
                            data_source.uuid,
                        )
                        or data_source.created is None
                        or data_source.last_modified is None
                        or data_source.size_bytes < 0
                    ):
                        raise ValueError("Failed to load Data")
                    data_sources.append(data_source)
                return data_sources
        except Exception as e:
            raise e

    def load(self) -> bool:
        if not validate_strings(self.url):
            self.logger.error(
                "Invalid url",
                method=self.load.__name__,
                url=self.url,
                format=self.format,
                description=self.description,
                size_bytes=self.size_bytes,
            )
            raise ValueError("Invalid url")
        try:
            self.verify_connection()
            self.logger.debug(
                "Loading Data",
                method=self.load.__name__,
                url=self.url,
                format=self.format,
                description=self.description,
                size_bytes=self.size_bytes,
            )
            records, _, _ = self.driver.execute_query(
                f"MATCH (a:{self.LABEL} {{url: $url}}) RETURN a", url=self.url, database_=self.db
            )
            if records:
                self.logger.debug(
                    "Data loaded",
                    method=self.load.__name__,
                    url=self.url,
                    format=self.format,
                    description=self.description,
                    size_bytes=self.size_bytes,
                )
                data = records[0].data().get("a", {})
                self.url = data.get("url", "")
                self.format = data.get("format", "")
                self.description = data.get("description", "")
                self.size_bytes = data.get("size_bytes", 0)
                self.uuid = data.get("uuid", "")
                self.created = data.get("created", None)
                self.last_modified = data.get("last_modified", None)
                if (
                    not validate_strings(self.url, self.format, self.uuid)
                    or self.created is None
                    or self.last_modified is None
                    or self.size_bytes < 0
                ):
                    self.logger.error(
                        "Failed to properly load Data",
                        method=self.load.__name__,
                        url=self.url,
                        format=self.format,
                        description=self.description,
                        size_bytes=self.size_bytes,
                        uuid=self.uuid,
                        created=self.created,
                        last_modified=self.last_modified,
                    )
                    raise ValueError("Failed to load Data")
            return True if records else False
        except Exception as e:
            self.logger.error(
                "Failed to load Data",
                method=self.load.__name__,
                error=str(e),
                url=self.url,
                format=self.format,
                description=self.description,
                size_bytes=self.size_bytes,
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
