import logging
import uuid

import structlog
from neo4j import Driver
from shared.models.base_model import BaseModel
from shared.utils.constants import FAILED_TO_CREATE_AUTHOR
from shared.utils.utils import get_storage_key_datetime, validate_strings

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


class Author(BaseModel):

    FIELDS_CSV = "last_name|first_name|uuid|created|last_modified\n"
    LABEL = "Author"

    def __init__(self, driver: Driver = None, last_name: str = "", first_name: str = ""):
        super().__init__(driver)
        if last_name and not validate_strings(last_name):
            message = "last_name must be a valid string if provided"
            self.logger.error(message, method=self.__init__.__name__)
            raise ValueError(message)
        if first_name and not validate_strings(first_name):
            message = "first_name must be a valid string if provided"
            self.logger.error(message, method=self.__init__.__name__)
            raise ValueError(message)
        self.first_name = first_name
        self.last_name = last_name
        self.uuid = None
        self.created = None
        self.last_modified = None

    def create(self, last_name: str = "", first_name: str = ""):
        if not validate_strings(self.first_name, self.last_name) and not validate_strings(first_name, last_name):
            message = "Invalid first_name, storage last_name,"
            self.logger.error(message, first_name=first_name, last_name=last_name, method=self.create.__name__)
            raise ValueError(message)
        try:
            self.first_name = first_name if validate_strings(first_name) else self.first_name
            self.last_name = last_name if validate_strings(last_name) else self.last_name
            self.verify_connection()
            self.logger.debug(
                "Creating Author",
                method=self.create.__name__,
                first_name=self.first_name,
                last_name=self.last_name,
            )
            now = get_storage_key_datetime()
            properties = {
                "uuid": str(uuid.uuid4()),
                "created": now,
                "last_modified": now,
            }
            records, summary, _ = self.driver.execute_query(
                """
                MERGE (a:Author {first_name: $first_name, last_name: $last_name})
                ON CREATE SET a += $props
                RETURN a""",
                first_name=self.first_name,
                last_name=self.last_name,
                props=properties,
                database_=self.db,
            )
            if records and summary.counters.nodes_created == 1:
                self.logger.debug(
                    "Author created", method=self.create.__name__, last_name=self.last_name, first_name=self.first_name
                )
            elif records and summary.counters.nodes_created == 0:
                self.logger.debug(
                    "Author already exists",
                    method=self.create.__name__,
                    last_name=self.last_name,
                    first_name=self.first_name,
                )
            else:
                self.logger.error(
                    FAILED_TO_CREATE_AUTHOR,
                    method=self.create.__name__,
                    last_name=self.last_name,
                    first_name=self.first_name,
                )
                raise RuntimeError()
            data = records[0].data().get("a", {})
            self.first_name = data.get("first_name", "")
            self.last_name = data.get("last_name", "")
            self.uuid = data.get("uuid", "")
            self.created = data.get("created", None)
            self.last_modified = data.get("last_modified", None)
            if not validate_strings(self.uuid) or self.created is None or self.last_modified is None:
                self.logger.error(
                    "Failed to properly create Author",
                    method=self.create.__name__,
                    first_name=self.first_name,
                    last_name=self.last_name,
                    uuid=self.uuid,
                    created=self.created,
                    last_modified=self.last_modified,
                )
                raise ValueError("Failed to create Author")
        except Exception as e:
            self.logger.error("Error while creating Author", method=self.create.__name__, error=str(e))
            raise e

    @classmethod
    def find(cls, driver: Driver, last_name: str, first_name: str = ""):
        if not driver or not isinstance(driver, Driver):
            raise ValueError("Invalid driver")
        if not validate_strings(last_name, first_name):
            raise ValueError("Invalid last_name or first_name")
        try:
            driver.verify_connectivity()
            records, _, _ = driver.execute_query(
                f"MATCH (a:{Author.LABEL} {{last_name: $last_name, first_name: $first_name}}) RETURN a",
                last_name=last_name,
                first_name=first_name,
                database_="neo4j",
            )
            if records and records[0] and records[0].data():
                data = records[0].data().get("a", {})
                author = Author(
                    driver=driver,
                    last_name=data.get("last_name", ""),
                    first_name=data.get("first_name", ""),
                )
                author.uuid = data.get("uuid", "")
                author.created = data.get("created", None)
                author.last_modified = data.get("last_modified", None)
                if (
                    not validate_strings(
                        author.first_name,
                        author.last_name,
                        author.uuid,
                    )
                    or author.created is None
                    or author.last_modified is None
                ):
                    raise ValueError("Failed to load Author")
                return author
            return None
        except Exception as e:
            raise e

    @classmethod
    def find_all(cls, driver: Driver):
        try:
            driver.verify_connectivity()
            records, _, _ = driver.execute_query(f"MATCH (a:{Author.LABEL}) RETURN a", database_="neo4j")
            if records:
                authors = []
                for record in records:
                    data = record.data().get("a", {})
                    author = Author(
                        driver=driver,
                        last_name=data.get("last_name", ""),
                        first_name=data.get("first_name", ""),
                    )
                    author.uuid = data.get("uuid")
                    author.created = data.get("created")
                    author.last_modified = data.get("last_modified")
                    if (
                        not validate_strings(
                            author.first_name,
                            author.last_name,
                            author.uuid,
                        )
                        or author.created is None
                        or author.last_modified is None
                    ):
                        raise ValueError("Failed to load Author")
                    authors.append(author)
                return authors
        except Exception as e:
            raise e

    def load(self) -> bool:
        if not validate_strings(self.last_name, self.first_name):
            message = "Invalid last_name or first_name"
            self.logger.error(message, method=self.load.__name__, first_name=self.first_name, last_name=self.last_name)
            raise ValueError(message)
        try:
            self.verify_connection()
            self.logger.debug(
                "Loading Author",
                method=self.load.__name__,
                first_name=self.first_name,
                last_name=self.last_name,
            )
            records, _, _ = self.driver.execute_query(
                f"MATCH (a:{self.LABEL} {{last_name: $last_name, first_name: $first_name}}) RETURN a",
                last_name=self.last_name,
                first_name=self.first_name,
                database_=self.db,
            )
            if records:
                self.logger.debug(
                    "Author loaded",
                    method=self.load.__name__,
                    first_name=self.first_name,
                    last_name=self.last_name,
                )
                data = records[0].data().get("a", {})
                self.first_name = data.get("first_name", "")
                self.last_name = data.get("last_name", "")
                self.uuid = data.get("uuid", "")
                self.created = data.get("created", None)
                self.last_modified = data.get("last_modified", None)
                if (
                    not validate_strings(self.first_name, self.last_name, self.uuid)
                    or self.created is None
                    or self.last_modified is None
                ):
                    self.logger.error(
                        "Failed to properly load Author",
                        method=self.load.__name__,
                        first_name=self.first_name,
                        last_name=self.last_name,
                        uuid=self.uuid,
                        created=self.created,
                        last_modified=self.last_modified,
                    )
                    raise ValueError("Failed to load Author")
            return True if records else False
        except Exception as e:
            self.logger.error(
                "Failed to load Author",
                method=self.load.__name__,
                error=str(e),
                first_name=self.first_name,
                last_name=self.last_name,
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
