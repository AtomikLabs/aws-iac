import uuid

import structlog
from constants import FAILED_TO_CREATE_ARXIV_CATEGORY, S3_KEY_DATE_FORMAT
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


class ArxivCategory(BaseModel):

    LABEL = "ArxivCategory"

    def __init__(self, driver: Driver = None, code: str = "", name: str = ""):
        super().__init__(driver)
        self.code = code
        self.name = name
        self.uuid = None
        self.created = None
        self.last_modified = None

    def create(self, code: str = "", name: str = ""):
        if not validate_strings(self.code, self.name) and not validate_strings(code, name):
            self.logger.error("Invalid code or name", method=self.create.__name__)
            raise ValueError("Invalid code or name")
        try:
            self.code = code if validate_strings(code) else self.code
            self.name = name if validate_strings(name) else self.name
            self.verify_connection()
            self.logger.debug("Creating ArxivCategory", method=self.create.__name__, code=self.code, name=self.name)
            now = get_storage_key_datetime().strftime(S3_KEY_DATE_FORMAT)
            properties = {
                "code": self.code,
                "uuid": str(uuid.uuid4()),
                "name": self.name,
                "created": now,
                "last_modified": now,
            }
            records, summary, _ = self.driver.execute_query(
                """
                MERGE (a:ArxivCategory {code: $code})
                ON CREATE SET a = $props
                RETURN a""",
                code=self.code,
                props=properties,
                database_=self.db,
            )
            if records and summary.counters.nodes_created == 1:
                self.logger.debug("ArxivCategory created", method=self.create.__name__, code=self.code, name=self.name)
            elif records and summary.counters.nodes_created == 0:
                self.logger.debug(
                    "ArxivCategory already exists", method=self.create.__name__, code=self.code, name=self.name
                )
            else:
                self.logger.error(
                    FAILED_TO_CREATE_ARXIV_CATEGORY, method=self.create.__name__, code=self.code, name=self.name
                )
                raise RuntimeError()
            data = records[0].data().get("a", {})
            print(data)
            self.name = data.get("name", "")
            self.uuid = data.get("uuid", "")
            self.created = data.get("created", "")
            self.last_modified = data.get("last_modified", "")
            if not validate_strings(self.uuid, self.created, self.last_modified):
                self.logger.error(
                    "Failed to properly create ArxivCategory",
                    method=self.create.__name__,
                    code=self.code,
                    name=self.name,
                    uuid=self.uuid,
                    created=self.created,
                    last_modified=self.last_modified,
                    node=data,
                )
                raise ValueError("Failed to create ArxivCategory")
        except Exception as e:
            self.logger.error("Error while creating ArxivCategory", method=self.create.__name__, error=str(e))
            raise e

    @classmethod
    def find(cls, driver: Driver, code: str):
        if not driver or not isinstance(driver, Driver):
            raise ValueError("Invalid driver")
        if not validate_strings(code):
            raise ValueError("Invalid code")
        try:
            driver.verify_connectivity()
            records, _, _ = driver.execute_query(
                f"MATCH (a:{ArxivCategory.LABEL} {{code: $code}}) RETURN a", code=code, database_="neo4j"
            )
            if records and records[0] and records[0].data():
                data = records[0].data().get("a", {})
                print(data)
                arxiv_category = ArxivCategory(
                    driver=driver,
                    code=data.get("code", ""),
                    name=data.get("name", ""),
                )
                arxiv_category.uuid = data.get("uuid", "")
                arxiv_category.created = data.get("created", "")
                arxiv_category.last_modified = data.get("last_modified", "")
                if not validate_strings(
                    arxiv_category.code,
                    arxiv_category.name,
                    arxiv_category.uuid,
                    arxiv_category.created,
                    arxiv_category.last_modified,
                ):
                    raise ValueError("Failed to load ArxivCategory")
                return arxiv_category
            return None
        except Exception as e:
            structlog.get_logger().error("Failed to find ArxivCategory", method=cls.find.__name__, error=str(e))
            raise e

    @classmethod
    def find_all(cls, driver: Driver):
        try:
            driver.verify_connectivity()
            records, _, _ = driver.execute_query(f"MATCH (a:{ArxivCategory.LABEL}) RETURN a", database_="neo4j")
            if records:
                arxiv_categories = []
                for record in records:
                    data = record.data().get("a", {})
                    arxiv_category = ArxivCategory(
                        driver=driver,
                        code=data.get("code", ""),
                        name=data.get("name", ""),
                    )
                    arxiv_category.uuid = data.get("uuid", "")
                    arxiv_category.created = data.get("created", "")
                    arxiv_category.last_modified = data.get("last_modified", "")
                    if not validate_strings(
                        arxiv_category.code,
                        arxiv_category.name,
                        arxiv_category.uuid,
                        arxiv_category.created,
                        arxiv_category.last_modified,
                    ):
                        raise ValueError("Failed to load ArxivCategory")
                    arxiv_categories.append(arxiv_category)
                return arxiv_categories
        except Exception as e:
            structlog.get_logger().error(
                "Failed to find all ArxivCategories", method=cls.find_all.__name__, error=str(e)
            )
            raise e

    def load(self) -> bool:
        if not validate_strings(self.code):
            self.logger.error("Invalid code", method=self.load.__name__, code=self.code, name=self.name)
            raise ValueError("Invalid code")
        try:
            self.verify_connection()
            self.logger.debug("Loading ArxivCategory", method=self.load.__name__, code=self.code, name=self.name)
            records, _, _ = self.driver.execute_query(
                f"MATCH (a:{self.LABEL} {{code: $code}}) RETURN a", code=self.code, database_=self.db
            )
            if records:
                self.logger.debug("ArxivCategory loaded", method=self.load.__name__, code=self.code, name=self.name)
                data = records[0].data().get("a", {})
                self.code = data.get("code", "")
                self.name = data.get("name", "")
                self.uuid = data.get("uuid", "")
                self.created = data.get("created", "")
                self.last_modified = data.get("last_modified", "")
                if not validate_strings(self.code, self.name, self.uuid, self.created, self.last_modified):
                    self.logger.error(
                        "Failed to properly load ArxivCategory",
                        method=self.load.__name__,
                        code=self.code,
                        name=self.name,
                        uuid=self.uuid,
                        created=self.created,
                        last_modified=self.last_modified,
                    )
                    raise ValueError("Failed to load ArxivCategory")
            return True if records else False
        except Exception as e:
            self.logger.error(
                "Failed to load ArxivCategory", method=self.load.__name__, error=str(e), code=self.code, name=self.name
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