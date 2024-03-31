import uuid

import structlog
from constants import FAILED_TO_CREATE_ARXIV_CATEGORY
from models.base_model import BaseModel
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
            self.code = code if code else self.code
            self.name = name if name else self.name
            self.verify_connection()
            self.logger.debug("Creating ArxivCategory", method=self.create.__name__, code=self.code, name=self.name)
            records, summary, _ = self.driver.execute_query(
                """
                MERGE (a:ArxivCategory {code: $code})
                ON CREATE SET a.created=TIMESTAMP(), a.last_modified=TIMESTAMP(), a.uuid=$uuid, a.name=$name
                RETURN a""",
                name=self.name,
                code=self.code,
                uuid=str(uuid.uuid4()),
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
            data = records[0].data()
            self.name = data["a"]["name"]
            self.uuid = data["a"]["uuid"]
            self.created = data["a"]["created"]
            self.last_modified = data["a"]["last_modified"]
            if not validate_strings(self.uuid, self.created, self.last_modified):
                self.logger.error(
                    "Failed to properly create ArxivCategory",
                    method=self.create.__name__,
                    code=self.code,
                    name=self.name,
                    uuid=self.uuid,
                    created=self.created,
                    last_modified=self.last_modified,
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
                f"MATCH (a:{cls.LABEL} {{code: $code}}) RETURN a", code=code, database_="neo4j"
            )
            if records and records[0] and records[0].data():
                data = records[0].data()
                ARXIV_CATEGORY = cls(
                    driver=driver,
                    code=data.get("a", {}).get("code", ""),
                    name=data.get("a", {}).get("name", ""),
                )
                ARXIV_CATEGORY.uuid = data.get("a", {}).get("uuid", "")
                ARXIV_CATEGORY.created = data.get("a", {}).get("created", "")
                ARXIV_CATEGORY.last_modified = data.get("a", {}).get("last_modified", "")
                if not validate_strings(
                    ARXIV_CATEGORY.code,
                    ARXIV_CATEGORY.name,
                    ARXIV_CATEGORY.uuid,
                    ARXIV_CATEGORY.created,
                    ARXIV_CATEGORY.last_modified,
                ):
                    raise ValueError("Failed to load ArxivCategory")
                return ARXIV_CATEGORY
            return None
        except Exception as e:
            raise e

    @classmethod
    def find_all(cls, driver: Driver):
        try:
            driver.verify_connectivity()
            records, _, _ = driver.execute_query(f"MATCH (a:{cls.LABEL}) RETURN a", database_="neo4j")
            if records:
                ARXIV_CATEGORYs = []
                for record in records:
                    data = record.data()["a"]
                    ARXIV_CATEGORY = cls(
                        driver=driver,
                        code=data["code"],
                        name=data["name"],
                    )
                    ARXIV_CATEGORY.uuid = data["uuid"]
                    ARXIV_CATEGORY.created = data["created"]
                    ARXIV_CATEGORY.last_modified = data["last_modified"]
                    if not validate_strings(
                        ARXIV_CATEGORY.code,
                        ARXIV_CATEGORY.name,
                        ARXIV_CATEGORY.uuid,
                        ARXIV_CATEGORY.created,
                        ARXIV_CATEGORY.last_modified,
                    ):
                        raise ValueError("Failed to load ArxivCategory")
                    ARXIV_CATEGORYs.append(ARXIV_CATEGORY)
                return ARXIV_CATEGORYs
        except Exception as e:
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
                self.code = records[0].data()["a"]["code"]
                self.name = records[0].data()["a"]["name"]
                self.uuid = records[0].data()["a"]["uuid"]
                self.created = records[0].data()["a"]["created"]
                self.last_modified = records[0].data()["a"]["last_modified"]
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
