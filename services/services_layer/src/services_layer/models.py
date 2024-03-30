import uuid
from abc import ABC, abstractmethod

import structlog
from constants import FAILED_TO_CREATE_ARXIV_SET
from neo4j import Driver
from utils import validate_strings

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


class BaseModel(ABC):
    def __init__(self, driver: Driver, db: str = "neo4j"):
        self.logger = structlog.get_logger()
        if not driver or not isinstance(driver, Driver):
            self.logger.error("Invalid driver", method=self.__init__.__name__, driver=driver, db=db)
            raise ValueError("Invalid driver")
        if not validate_strings(db):
            self.logger.error("Invalid database name", method=self.__init__.__name__, driver=driver, db=db)
            raise ValueError("Invalid database name")
        self.driver = driver
        self.db = db
        self.relationships = []
        self.uuid = None

    @abstractmethod
    def create(self) -> dict:
        pass

    @abstractmethod
    def load(self) -> dict:
        pass

    def verify_connection(self):
        try:
            self.driver.verify_connectivity()
            self.logger.debug("Connection verified", method=self.verify_connection.__name__)
        except AttributeError as e:
            self.logger.error(
                "Driver is of the wrong type, was a new value assigned to the driver?",
                method=self.verify_connection.__name__,
                error=str(e),
            )
            raise e
        except Exception as e:
            self.logger.error("Connection failed", method=self.verify_connection.__name__, error=str(e))
            raise e


class ArxivSet(BaseModel):
    def __init__(self, driver: Driver, code: str, name: str):
        super().__init__(driver)
        if not validate_strings(code):
            self.logger.error("Invalid code", method=self.__init__.__name__, code=code)
            raise ValueError("Invalid code")
        self.code = code
        self.name = name
        self.uuid = None
        self.created = None
        self.last_modified = None

    def create(self):
        if not validate_strings(self.code, self.name):
            self.logger.error("Invalid code or name", method=self.create.__name__, code=self.code, name=self.name)
            raise ValueError("Invalid code or name")
        try:
            self.verify_connection()
            self.logger.debug("Creating ArxivSet", method=self.create.__name__, code=self.code, name=self.name)
            records, summary, _ = self.driver.execute_query(
                """
                MERGE (a:ArxivSet {code: $code})
                ON CREATE SET a.created=TIMESTAMP(), a.last_modified=TIMESTAMP(), a.uuid=$uuid, a.name=$name
                RETURN a""",
                name=self.name,
                code=self.code,
                uuid=str(uuid.uuid4()),
                database_=self.db,
            )
            if records and summary.counters.nodes_created == 1:
                self.logger.debug("ArxivSet created", method=self.create.__name__, code=self.code, name=self.name)
            elif records and summary.counters.nodes_created == 0:
                self.logger.debug(
                    "ArxivSet already exists", method=self.create.__name__, code=self.code, name=self.name
                )
            else:
                self.logger.error(
                    FAILED_TO_CREATE_ARXIV_SET, method=self.create.__name__, code=self.code, name=self.name
                )
                raise RuntimeError()
            data = records[0].data()
            self.name = data["a"]["name"]
            self.uuid = data["a"]["uuid"]
            self.created = data["a"]["created"]
            self.last_modified = data["a"]["last_modified"]
            if not validate_strings(self.uuid, self.created, self.last_modified):
                self.logger.error(
                    "Failed to properly create ArxivSet",
                    method=self.create.__name__,
                    code=self.code,
                    name=self.name,
                    uuid=self.uuid,
                    created=self.created,
                    last_modified=self.last_modified,
                )
                raise ValueError("Failed to create ArxivSet")
        except Exception as e:
            self.logger.error("Error while creating ArxivSet", method=self.create.__name__, error=str(e))
            raise e

    def load(self) -> bool:
        if not validate_strings(self.code):
            self.logger.error("Invalid code", method=self.load.__name__, code=self.code, name=self.name)
            raise ValueError("Invalid code")
        try:
            self.verify_connection()
            self.logger.debug("Loading ArxivSet", method=self.load.__name__, code=self.code, name=self.name)
            records, _, _ = self.driver.execute_query(
                "MATCH (a:ArxivSet {code: $code}) RETURN a", code=self.code, database_=self.db
            )
            if records:
                self.logger.debug("ArxivSet loaded", method=self.load.__name__, code=self.code, name=self.name)
                self.code = records[0]["a"]["code"]
                self.name = records[0]["a"]["name"]
                self.uuid = records[0]["a"]["uuid"]
                self.created = records[0]["a"]["created"]
                self.last_modified = records[0]["a"]["last_modified"]
                if not validate_strings(self.code, self.name, self.uuid, self.created, self.last_modified):
                    self.logger.error(
                        "Failed to properly load ArxivSet",
                        method=self.load.__name__,
                        code=self.code,
                        name=self.name,
                        uuid=self.uuid,
                        created=self.created,
                        last_modified=self.last_modified,
                    )
                    raise ValueError("Failed to load ArxivSet")
            return True if records else False
        except Exception as e:
            self.logger.error(
                "Failed to load ArxivSet", method=self.load.__name__, error=str(e), code=self.code, name=self.name
            )
            raise e
