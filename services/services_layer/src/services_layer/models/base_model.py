from abc import ABC, abstractmethod

import structlog
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
    def create(self):
        pass

    @abstractmethod
    def find(self, driver: Driver):
        pass

    @classmethod
    @abstractmethod
    def find_all(cls, driver: Driver):
        pass

    @classmethod
    @abstractmethod
    def load(cls) -> bool:
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


