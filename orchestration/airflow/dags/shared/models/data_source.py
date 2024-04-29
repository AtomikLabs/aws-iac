import logging
import uuid

import structlog
from dags.shared.models.base_model import BaseModel
from dags.shared.utils.constants import FAILED_TO_CREATE_DATA_SOURCE
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


class DataSource(BaseModel):

    LABEL = "DataSource"

    def __init__(self, driver: Driver = None, url: str = "", name: str = "", description: str = ""):
        super().__init__(driver)
        if url != "" and not validate_strings(url):
            self.logger.error("URL must be a valid string if provided", method=self.__init__.__name__)
            raise ValueError("URL must be a valid string if provided")
        if name != "" and not validate_strings(name):
            self.logger.error("Name must be a valid string if provided", method=self.__init__.__name__)
            raise ValueError("Name must be a valid string if provided")
        if description != "" and not validate_strings(description):
            self.logger.error("Description must be a valid string if provided", method=self.__init__.__name__)
            raise ValueError("Description must be a valid string if provided")
        self.url = url
        self.name = name
        self.description = description
        self.uuid = None
        self.created = None
        self.last_modified = None

    def create(self, url: str = "", name: str = "", description: str = ""):
        if not validate_strings(self.url, self.name, self.description) and not validate_strings(url, name, description):
            message = "Invalid url, name, or description"
            self.logger.error(message, method=self.create.__name__)
            raise ValueError(message)
        try:
            self.url = self.url if validate_strings(self.url) else url
            self.name = name if validate_strings(name) else self.name
            self.description = description if validate_strings(description) else self.description
            self.verify_connection()
            self.logger.debug(
                "Creating DataSource",
                method=self.create.__name__,
                url=self.url,
                name=self.name,
                description=self.description,
            )
            now = get_storage_key_datetime()
            properties = {
                "url": self.url,
                "uuid": str(uuid.uuid4()),
                "name": self.name,
                "description": self.description,
                "created": now,
                "last_modified": now,
            }
            records, summary, _ = self.driver.execute_query(
                """
                MERGE (a:DataSource {url: $url})
                ON CREATE SET a += $props
                RETURN a""",
                url=self.url,
                props=properties,
                database_=self.db,
            )
            if records and summary.counters.nodes_created == 1:
                self.logger.debug(
                    "DataSource created",
                    method=self.create.__name__,
                    url=self.url,
                    name=self.name,
                    description=self.description,
                )
            elif records and summary.counters.nodes_created == 0:
                self.logger.debug(
                    "DataSource already exists",
                    method=self.create.__name__,
                    url=self.url,
                    name=self.name,
                    description=self.description,
                )
            else:
                self.logger.error(
                    FAILED_TO_CREATE_DATA_SOURCE,
                    method=self.create.__name__,
                    url=self.url,
                    name=self.name,
                    description=self.description,
                )
                raise RuntimeError()
            data = records[0].data().get("a", {})
            self.name = data.get("name", "")
            self.uuid = data.get("uuid", "")
            self.description = data.get("description", "")
            self.created = data.get("created", None)
            self.last_modified = data.get("last_modified", None)
            if not validate_strings(self.uuid) or self.created is None or self.last_modified is None:
                self.logger.error(
                    "Failed to properly create DataSource",
                    method=self.create.__name__,
                    url=self.url,
                    name=self.name,
                    description=self.description,
                    uuid=self.uuid,
                    created=self.created,
                    last_modified=self.last_modified,
                )
                raise ValueError("Failed to create DataSource")
        except Exception as e:
            self.logger.error("Error while creating DataSource", method=self.create.__name__, error=str(e))
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
                f"MATCH (a:{DataSource.LABEL} {{url: $url}}) RETURN a", url=url, database_="neo4j"
            )
            if records and records[0] and records[0].data():
                data = records[0].data().get("a", {})
                data_source = DataSource(
                    driver=driver,
                    url=data.get("url", ""),
                    name=data.get("name", ""),
                    description=data.get("description", ""),
                )
                data_source.uuid = data.get("uuid", "")
                data_source.created = data.get("created", None)
                data_source.last_modified = data.get("last_modified", None)
                if (
                    not validate_strings(data_source.url, data_source.name, data_source.uuid)
                    or data_source.created is None
                    or data_source.last_modified is None
                ):
                    raise ValueError("Failed to load DataSource")
                return data_source
            return None
        except Exception as e:
            raise e

    @classmethod
    def find_all(cls, driver: Driver):
        try:
            driver.verify_connectivity()
            records, _, _ = driver.execute_query(f"MATCH (a:{DataSource.LABEL}) RETURN a", database_="neo4j")
            if records:
                data_sources = []
                for record in records:
                    data = record.data().get("a", {})
                    data_source = DataSource(
                        driver=driver,
                        url=data.get("url"),
                        name=data.get("name"),
                        description=data.get("description"),
                    )
                    data_source.uuid = data.get("uuid")
                    data_source.created = data.get("created")
                    data_source.last_modified = data.get("last_modified")
                    if not validate_strings(
                        data_source.url,
                        data_source.name,
                        data_source.uuid,
                    ):
                        raise ValueError("Failed to load DataSource")
                    data_sources.append(data_source)
                return data_sources
        except Exception as e:
            raise e

    def load(self) -> bool:
        if not validate_strings(self.url):
            self.logger.error(
                "Invalid url", method=self.load.__name__, url=self.url, name=self.name, description=self.description
            )
            raise ValueError("Invalid url")
        try:
            self.verify_connection()
            self.logger.debug("Loading DataSource", method=self.load.__name__, url=self.url, name=self.name)
            records, _, _ = self.driver.execute_query(
                f"MATCH (a:{self.LABEL} {{url: $url}}) RETURN a", url=self.url, database_=self.db
            )
            if records:
                self.logger.debug("DataSource loaded", method=self.load.__name__, url=self.url, name=self.name)
                data = records[0].data().get("a", {})
                self.url = data.get("url", "")
                self.name = data.get("name", "")
                self.description = data.get("description", "")
                self.uuid = data.get("uuid", "")
                self.created = data.get("created", None)
                self.last_modified = data.get("last_modified", None)
                if (
                    not validate_strings(self.url, self.name, self.uuid)
                    or self.created is None
                    or self.last_modified is None
                ):
                    self.logger.error(
                        "Failed to properly load DataSource",
                        method=self.load.__name__,
                        url=self.url,
                        name=self.name,
                        description=self.description,
                        uuid=self.uuid,
                        created=self.created,
                        last_modified=self.last_modified,
                    )
                    raise ValueError("Failed to load DataSource")
            return True if records else False
        except Exception as e:
            self.logger.error(
                "Failed to load DataSource",
                method=self.load.__name__,
                error=str(e),
                url=self.url,
                name=self.name,
                description=self.description,
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
