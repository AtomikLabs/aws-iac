import structlog
from neo4j import GraphDatabase

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

class BaseModel:   
    def __init__(self, driver: GraphDatabase.driver):
        self.driver = driver
        self.logger = structlog.get_logger()

    def verify_connection(self):
        try:
            self.driver.verify_connectivity()
            self.logger.debug("Connection verified", method=self.verify_connection.__name__)
        except Exception as e:
            self.logger.error("Connection failed", method=self.verify_connection.__name__, error=str(e))
            raise e