import logging
import uuid

import structlog
from dags.shared.models.base_model import BaseModel
from dags.shared.utils.constants import FAILED_TO_CREATE_DATA_OPERATION
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


class DataOperation(BaseModel):

    LABEL = "DataOperation"

    def __init__(self, driver: Driver = None, name: str = "", method_name: str = "", method_version: str = ""):
        super().__init__(driver)
        if not isinstance(driver, Driver):
            message = "Invalid driver provided"
            self.logger.error(message, method=self.__init__.__name__)
            raise ValueError(message)
        if name != "" and not validate_strings(name):
            message = "Name must be a valid string if provided"
            self.logger.error(message, method=self.__init__.__name__)
            raise ValueError(message)
        if method_name != "" and not validate_strings(method_name):
            message = "Method name must be a valid string if provided"
            self.logger.error(message, method=self.__init__.__name__)
            raise ValueError(message)
        if method_version != "" and not validate_strings(method_version):
            message = "Method version must be a valid string if provided"
            self.logger.error(message, method=self.__init__.__name__)
            raise ValueError(message)
        self.name = name
        self.method_name = method_name
        self.method_version = method_version
        self.uuid = None
        self.created = None
        self.last_modified = None

    def create(self, name: str = "", method_name: str = "", method_version: str = ""):
        if not validate_strings(self.name, self.method_name, self.method_version) and not validate_strings(
            name, self.method_name, self.method_version
        ):
            message = "Invalid name, method_name, or method_version"
            self.logger.error(message, method=self.create.__name__)
            raise ValueError(message)
        try:
            self.name = name if validate_strings(name) else self.name
            self.method_name = method_name if validate_strings(method_name) else self.method_name
            self.method_version = method_version if validate_strings(method_version) else self.method_version
            self.verify_connection()
            self.logger.debug(
                "Creating DataOperation",
                method=self.create.__name__,
                name=self.name,
                dop_method_name=self.method_name,
                dop_method_version=self.method_version,
            )
            now = get_storage_key_datetime()
            properties = {
                "uuid": str(uuid.uuid4()),
                "name": self.name,
                "method_name": self.method_name,
                "method_version": self.method_version,
                "last_modified": now,
            }
            records, summary, _ = self.driver.execute_query(
                """
                MERGE (a:DataOperation {name: $name, created: $created})
                ON CREATE SET a += $props
                RETURN a""",
                name=self.name,
                created=now,
                props=properties,
                database_=self.db,
            )
            if records and summary.counters.nodes_created == 1:
                self.logger.debug(
                    "DataOperation created",
                    method=self.create.__name__,
                    name=self.name,
                    dop_method_name=self.method_name,
                    dop_method_version=self.method_version,
                )
            elif records and summary.counters.nodes_created == 0:
                self.logger.debug(
                    "DataOperation already exists",
                    method=self.create.__name__,
                    name=self.name,
                    dop_method_name=self.method_name,
                    dop_method_version=self.method_version,
                )
            else:
                self.logger.error(
                    FAILED_TO_CREATE_DATA_OPERATION,
                    method=self.create.__name__,
                    name=self.name,
                    dop_method_name=self.method_name,
                    dop_method_version=self.method_version,
                )
                raise RuntimeError()
            data = records[0].data().get("a", {})
            self.name = data.get("name", "")
            self.method_name = data.get("method_name", "")
            self.method_version = data.get("method_version", "")
            self.uuid = data.get("uuid", "")
            self.created = data.get("created", None)
            self.last_modified = data.get("last_modified", None)
            if not validate_strings(self.uuid) or self.created is None or self.last_modified is None:
                self.logger.error(
                    "Failed to properly create DataOperation",
                    method=self.create.__name__,
                    name=self.name,
                    dop_method_name=self.method_name,
                    dop_method_version=self.method_version,
                    uuid=self.uuid,
                    created=self.created,
                    last_modified=self.last_modified,
                )
                raise ValueError("Failed to create DataOperation")
        except Exception as e:
            self.logger.error(
                "Error while creating DataOperation",
                method=self.create.__name__,
                dop_dop_method_name=self.method_name,
                dop_dop_method_version=self.method_version,
                error=str(e),
            )
            raise e

    @classmethod
    def find(cls, driver: Driver, name: str):
        raise NotImplementedError()

    @classmethod
    def find_all(cls, driver: Driver):
        try:
            driver.verify_connectivity()
            records, _, _ = driver.execute_query(f"MATCH (a:{DataOperation.LABEL}) RETURN a", database_="neo4j")
            if records:
                data_operations = []
                for record in records:
                    data = record.data().get("a", {})
                    data_operation = DataOperation(
                        driver=driver,
                        name=data.get("name"),
                        method_name=data.get("method_name"),
                        method_version=data.get("method_version"),
                    )
                    data_operation.uuid = data.get("uuid")
                    data_operation.created = data.get("created")
                    data_operation.last_modified = data.get("last_modified")
                    if (
                        not validate_strings(
                            data_operation.code,
                            data_operation.name,
                            data_operation.method_name,
                            data_operation.method_version,
                            data_operation.uuid,
                        )
                        or data_operation.created is None
                        or data_operation.last_modified is None
                    ):
                        raise ValueError("Failed to load DataOperation")
                    data_operations.append(data_operation)
                return data_operations
        except Exception as e:
            raise e

    def load(self) -> bool:
        raise NotImplementedError()

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
