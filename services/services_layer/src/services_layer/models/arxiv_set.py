import structlog
import uuid
from constants import FAILED_TO_CREATE_ARXIV_SET
from neo4j import Driver
from utils import validate_strings

from models.base_model import BaseModel

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

class ArxivSet(BaseModel):

    LABEL = "ArxivSet"

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
                arxiv_set = cls(
                    driver=driver,
                    code=data.get("a", {}).get("code", ""),
                    name=data.get("a", {}).get("name", ""),
                )
                arxiv_set.uuid = data.get("a", {}).get("uuid", "")
                arxiv_set.created = data.get("a", {}).get("created", "")
                arxiv_set.last_modified = data.get("a", {}).get("last_modified", "")
                if not validate_strings(arxiv_set.code, arxiv_set.name, arxiv_set.uuid, arxiv_set.created, arxiv_set.last_modified):
                    raise ValueError("Failed to load ArxivSet")
                return arxiv_set
            return None
        except Exception as e:
            raise e
    
    @classmethod
    def find_all(cls, driver: Driver):
        try:
            driver.verify_connectivity()
            records, _, _ = driver.execute_query(f"MATCH (a:{cls.LABEL}) RETURN a", database_="neo4j")
            if records:
                arxiv_sets = []
                for record in records:
                    data = record.data()["a"]
                    arxiv_set = cls(
                        driver=driver,
                        code=data["code"],
                        name=data["name"],
                    )
                    arxiv_set.uuid = data["uuid"]
                    arxiv_set.created = data["created"]
                    arxiv_set.last_modified = data["last_modified"]
                    if not validate_strings(arxiv_set.code, arxiv_set.name, arxiv_set.uuid, arxiv_set.created, arxiv_set.last_modified):
                        raise ValueError("Failed to load ArxivSet")
                    arxiv_sets.append(arxiv_set)
                return arxiv_sets
        except Exception as e:
            raise e

    def load(self) -> bool:
        if not validate_strings(self.code):
            self.logger.error("Invalid code", method=self.load.__name__, code=self.code, name=self.name)
            raise ValueError("Invalid code")
        try:
            self.verify_connection()
            self.logger.debug("Loading ArxivSet", method=self.load.__name__, code=self.code, name=self.name)
            records, _, _ = self.driver.execute_query(
                f"MATCH (a:{self.LABEL} {{code: $code}}) RETURN a", code=self.code, database_=self.db
            )
            if records:
                self.logger.debug("ArxivSet loaded", method=self.load.__name__, code=self.code, name=self.name)
                self.code = records[0].data()["a"]["code"]
                self.name = records[0].data()["a"]["name"]
                self.uuid = records[0].data()["a"]["uuid"]
                self.created = records[0].data()["a"]["created"]
                self.last_modified = records[0].data()["a"]["last_modified"]
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
