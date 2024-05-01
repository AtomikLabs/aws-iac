import logging
import uuid
from abc import ABC, abstractmethod

import structlog
from shared.utils.utils import get_storage_key_datetime, validate_strings
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


class BaseModel(ABC):

    RELATIONSHIP_CSV = "label|start_label|start_uuid|end_label|end_uuid|uuid|created|last_modified\n"

    def __init__(self, driver: Driver, db: str = "neo4j"):
        self.logger = structlog.get_logger()
        self.logger.setLevel(logging.INFO)
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

    @abstractmethod
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
        pass

    def _relate(
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
        if not validate_strings(label, start_label, start_uuid, end_label, end_uuid):
            raise ValueError("labels, start_node, and end_node must be valid strings")
        if not driver and not isinstance(driver, Driver):
            raise ValueError("Invalid driver")
        self.verify_connection()
        try:
            result, summary = None, None
            properties = properties if properties else {}
            now = get_storage_key_datetime()
            properties["uuid"] = str(uuid.uuid4())
            properties["created"] = now
            properties["last_modified"] = now
            if unique:
                result, summary, _ = driver.execute_query(
                    f"""
                    MATCH (start:{start_label} {{uuid: $start_uuid}})
                    MATCH (end:{end_label} {{uuid: $end_uuid}})
                    MERGE (start)-[r:{label}]->(end)
                    ON CREATE SET r += $props
                    RETURN r
                    """,
                    start_label=start_label,
                    end_label=end_label,
                    label=label,
                    start_uuid=start_uuid,
                    end_uuid=end_uuid,
                    props=properties,
                )
            else:
                result, summary, _ = driver.execute_query(
                    f"""
                    MATCH (start:{start_label} {{uuid: $start_uuid}})
                    MATCH (end:{end_label} {{uuid: $end_uuid}})
                    CREATE (start)-[r:{label}]->(end)
                    SET r += $props
                    RETURN r
                    """,
                    start_label=start_label,
                    end_label=end_label,
                    label=label,
                    start_uuid=start_uuid,
                    end_uuid=end_uuid,
                    props=properties,
                )

            if result and summary.counters.relationships_created == 1:
                self.logger.debug(
                    "Relationship created",
                    method=self.relate.__name__,
                    start_label=start_label,
                    start_node_uuid=start_uuid,
                    end_label=end_label,
                    end_node_uuid=end_uuid,
                    properties=properties,
                )
                return result
            elif result and summary.counters.relationships_created == 0:
                self.logger.debug(
                    "Relationship already exists",
                    method=self.relate.__name__,
                    start_label=start_label,
                    start_node_uuid=start_uuid,
                    end_label=end_label,
                    end_node_uuid=end_uuid,
                    properties=properties,
                )
                return result
            else:
                self.logger.error(
                    "Failed to create relationship",
                    method=self.relate.__name__,
                    start_label=start_label,
                    start_node_uuid=start_uuid,
                    end_label=end_label,
                    end_node_uuid=end_uuid,
                    properties=properties,
                )
                raise RuntimeError()
        except Exception as e:
            self.logger.error(
                "Failed to create relationship",
                method=self.relate.__name__,
                label=label,
                start_node_uuid=start_uuid,
                end_node_uuid=end_uuid,
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
