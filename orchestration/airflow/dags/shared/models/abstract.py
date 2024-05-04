import logging
import uuid

import structlog
from neo4j import Driver
from shared.models.base_model import BaseModel
from shared.utils.constants import FAILED_TO_CREATE_ABSTRACT
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


class Abstract(BaseModel):

    FIELDS_CSV = "url|bucket|key|uuid|created|last_modified\n"
    LABEL = "Abstract"

    def __init__(self, driver: Driver = None, url: str = "", bucket: str = "", key: str = ""):
        super().__init__(driver)
        if url and not validate_strings(url):
            message = "URL must be a valid string if provided"
            self.logger.error(message, method=self.__init__.__name__)
            raise ValueError(message)
        if bucket and not validate_strings(bucket):
            message = "Storage bucket must be a valid string if provided"
            self.logger.error(message, method=self.__init__.__name__)
            raise ValueError(message)
        if key and not validate_strings(key):
            message = "Key must be a valid string if provided"
            self.logger.error(message, method=self.__init__.__name__)
            raise ValueError(message)
        self.url = url
        self.bucket = bucket
        self.key = key
        self.uuid = None
        self.created = None
        self.last_modified = None

    def create(self, url: str = "", bucket: str = "", key: str = ""):
        if not validate_strings(self.url) and not validate_strings(url):
            message = "Invalid url"
            self.logger.error(message, method=self.create.__name__)
            raise ValueError(message)
        try:
            self.url = url if validate_strings(url) else self.url
            self.bucket = bucket if validate_strings(bucket) else self.bucket
            self.key = key if validate_strings(key) else self.key
            self.verify_connection()
            self.logger.debug(
                "Creating Abstract",
                method=self.create.__name__,
                key=self.key,
                url=self.url,
            )
            now = get_storage_key_datetime()
            properties = {
                "bucket": self.bucket,
                "key": self.key,
                "uuid": str(uuid.uuid4()),
                "created": now,
                "last_modified": now,
            }
            records, summary, _ = self.driver.execute_query(
                """
                MERGE (a:Abstract {url: $url})
                ON CREATE SET a += $props
                RETURN a""",
                url=self.url,
                props=properties,
                database_=self.db,
            )
            if records and summary.counters.nodes_created == 1:
                self.logger.debug("Abstract created", method=self.create.__name__, name=self.key)
            elif records and summary.counters.nodes_created == 0:
                self.logger.debug("Abstract already exists", method=self.create.__name__, name=self.key)
            else:
                self.logger.error(FAILED_TO_CREATE_ABSTRACT, method=self.create.__name__, name=self.key)
                raise RuntimeError()
            data = records[0].data().get("a", {})
            self.url = data.get("url", "")
            self.bucket = data.get("bucket", "")
            self.key = data.get("key", "")
            self.uuid = data.get("uuid", "")
            self.created = data.get("created", None)
            self.last_modified = data.get("last_modified", None)
            if not validate_strings(self.uuid) or self.created is None or self.last_modified is None:
                self.logger.error(
                    "Failed to properly create Abstract",
                    method=self.create.__name__,
                    key=self.key,
                    url=self.url,
                    uuid=self.uuid,
                    created=self.created,
                    last_modified=self.last_modified,
                )
                raise ValueError("Failed to create Abstract")
        except Exception as e:
            self.logger.error("Error while creating Abstract", method=self.create.__name__, error=str(e))
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
                f"MATCH (a:{Abstract.LABEL} {{url: $url}}) RETURN a", url=url, database_="neo4j"
            )
            if records and records[0] and records[0].data():
                data = records[0].data().get("a", {})
                abstract = Abstract(
                    driver=driver,
                    url=data.get("url", ""),
                    bucket=data.get("bucket", ""),
                    key=data.get("key", ""),
                )
                abstract.uuid = data.get("uuid", "")
                abstract.created = data.get("created", None)
                abstract.last_modified = data.get("last_modified", None)
                if (
                    not validate_strings(
                        abstract.url,
                        abstract.bucket,
                        abstract.key,
                        abstract.uuid,
                    )
                    or abstract.created is None
                    or abstract.last_modified is None
                ):
                    raise ValueError("Failed to load Abstract")
                return abstract
            return None
        except Exception as e:
            logger.error("Failed to find Abstract", error=str(e), url=url, method=cls.find.__name__)
            raise e

    @classmethod
    def find_all(cls, driver: Driver):
        try:
            driver.verify_connectivity()
            records, _, _ = driver.execute_query(f"MATCH (a:{Abstract.LABEL}) RETURN a", database_="neo4j")
            if records:
                abstracts = []
                for record in records:
                    data = record.data().get("a", {})
                    abstract = Abstract(
                        driver=driver,
                        url=data.get("url", ""),
                        bucket=data.get("bucket", ""),
                        key=data.get("key", ""),
                    )
                    abstract.uuid = data.get("uuid")
                    abstract.created = data.get("created")
                    abstract.last_modified = data.get("last_modified")
                    if (
                        not validate_strings(
                            abstract.url,
                            abstract.bucket,
                            abstract.key,
                            abstract.uuid,
                        )
                        or abstract.created is None
                        or abstract.last_modified is None
                    ):
                        raise ValueError("Failed to load Abstract")
                    abstracts.append(abstract)
                return abstracts
        except Exception as e:
            logger.error("Failed to find all Abstracts", error=str(e), method=cls.find_all.__name__)
            raise e

    def load(self) -> bool:
        if not validate_strings(self.url):
            self.logger.error("Invalid url", method=self.load.__name__, url=self.url, bucket=self.bucket, key=self.key)
            raise ValueError("Invalid url")
        try:
            self.verify_connection()
            self.logger.debug("Invalid url", method=self.load.__name__, url=self.url, bucket=self.bucket, key=self.key)
            records, _, _ = self.driver.execute_query(
                f"MATCH (a:{self.LABEL} {{url: $url}}) RETURN a", url=self.url, database_=self.db
            )
            if records:
                self.logger.debug(
                    "Abstract loaded",
                    method=self.load.__name__,
                    url=self.url,
                    bucket=self.bucket,
                    key=self.key,
                )
                data = records[0].data().get("a", {})
                self.url = data.get("url", "")
                self.bucket = data.get("bucket", "")
                self.key = data.get("key", "")
                self.uuid = data.get("uuid", "")
                self.created = data.get("created", None)
                self.last_modified = data.get("last_modified", None)
                if (
                    not validate_strings(self.url, self.key, self.bucket, self.uuid)
                    or self.created is None
                    or self.last_modified is None
                ):
                    self.logger.error(
                        "Failed to properly load Abstract",
                        method=self.load.__name__,
                        url=self.url,
                        bucket=self.bucket,
                        key=self.key,
                        uuid=self.uuid,
                        created=self.created,
                        last_modified=self.last_modified,
                    )
                    raise ValueError("Failed to load Abstract")
            return True if records else False
        except Exception as e:
            self.logger.error(
                "Failed to load Abstract",
                method=self.load.__name__,
                error=str(e),
                url=self.url,
                bucket=self.bucket,
                key=self.key,
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
