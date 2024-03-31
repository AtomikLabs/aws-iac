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

    def relate(self, driver: Driver, label: str, start_node_uuid: str, end_node_uuid: str, properties: dict):
        if not validate_strings(label, start_node_uuid, end_node_uuid):
            raise ValueError("label, start_node, and end_node must be valid strings")
        if not driver and not isinstance(driver, Driver):
            raise ValueError("Invalid driver")
        self.verify_connection()
        try:
            with driver.session(database=self.db) as session:
                query = (
                    f"MATCH (start:{label}),(end:{label}) "
                    f"WHERE start.uuid = $start_node_uuid AND end.uuid = $end_node_uuid "
                    f"CREATE (start)-[r:RELATED_TO]->(end) "
                    f"SET r = $properties "
                    f"RETURN r"
                )
                result = session.run(
                    query, start_node_uuid=start_node_uuid, end_node_uuid=end_node_uuid, properties=properties
                )
                self.logger.debug(
                    "Relationship created",
                    method=self.relate.__name__,
                    label=label,
                    start_node_uuid=start_node_uuid,
                    end_node_uuid=end_node_uuid,
                    properties=properties,
                )
                return result
        except Exception as e:
            self.logger.error(
                "Failed to create relationship",
                method=self.relate.__name__,
                label=label,
                start_node_uuid=start_node_uuid,
                end_node_uuid=end_node_uuid,
                properties=properties,
                error=str(e),
            )
            raise e

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
