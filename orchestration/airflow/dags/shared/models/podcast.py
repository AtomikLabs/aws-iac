import logging
import uuid
from datetime import date, datetime

import structlog
from neo4j import Driver
from shared.models.base_model import BaseModel
from shared.utils.utils import get_storage_key_datetime

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


class Podcast(BaseModel):

    FIELDS_CSV = "season|episode|date|uuid|created|last_modified\n"
    LABEL = "Podcast"

    def __init__(self, driver: Driver = None, season: int = 0, episode: int = 0, part=0, date: date = None):
        super().__init__(driver)
        if season and (not isinstance(season, int) or season < 0):
            message = "season must be a non-negative integer"
            self.logger.error(message, method=self.__init__.__name__)
            raise ValueError(message)
        if episode and (not isinstance(episode, int) or episode < 0):
            message = "episode must be a non-negative integer"
            self.logger.error(message, method=self.__init__.__name__)
            raise ValueError(message)
        if part and (not isinstance(part, int) or part < 0):
            message = "part must be a non-negative integer"
            self.logger.error(message, method=self.__init__.__name__)
            raise ValueError(message)
        if date and not isinstance(date, date):
            message = "date must be a valid date object"
            self.logger.error(message, method=self.__init__.__name__)
            raise ValueError(message)
        self.season = season
        self.episode = episode
        self.part = part
        self.date = date
        self.uuid = None
        self.created = None
        self.last_modified = None

    def create(self, season: int = None, episode: int = None, part: int = None, date: date = None):
        season = season if season is not None else self.season
        episode = episode if episode is not None else self.episode
        part = part if part is not None else self.part
        date = date if date is not None else self.date

        if season is None or episode is None or date is None:
            message = "season, episode, and date are required for creation"
            self.logger.error(message, method=self.create.__name__)
            raise ValueError(message)

        if not isinstance(season, int) or season < 0:
            message = "season must be a non-negative integer"
            self.logger.error(message, method=self.create.__name__)
            raise ValueError(message)
        if not isinstance(episode, int) or episode < 0:
            message = "episode must be a non-negative integer"
            self.logger.error(message, method=self.create.__name__)
            raise ValueError(message)
        if not isinstance(part, int) or part < 0:
            message = "part must be a non-negative integer"
            self.logger.error(message, method=self.create.__name__)
            raise ValueError(message)
        if not isinstance(date, date):
            message = "date must be a valid date object"
            self.logger.error(message, method=self.create.__name__)
            raise ValueError(message)

        try:
            self.season = season
            self.episode = episode
            self.part = part
            self.date = date
            self.verify_connection()
            self.logger.debug(
                "Creating Podcast",
                method=self.create.__name__,
                season=self.season,
                episode=self.episode,
                part=self.part,
                date=self.date,
            )
            now = get_storage_key_datetime()
            properties = {
                "uuid": str(uuid.uuid4()),
                "created": now,
                "last_modified": now,
            }
            records, summary, _ = self.driver.execute_query(
                """
                MERGE (p:Podcast {season: $season, episode: $episode, part: $part, date: $date})
                ON CREATE SET p += $props
                RETURN p""",
                season=self.season,
                episode=self.episode,
                part=self.part,
                date=self.date.isoformat(),
                props=properties,
                database_=self.db,
            )
            if records and summary.counters.nodes_created == 1:
                self.logger.debug(
                    "Podcast created",
                    method=self.create.__name__,
                    season=self.season,
                    episode=self.episode,
                    part=self.part,
                    date=self.date,
                )
            elif records and summary.counters.nodes_created == 0:
                self.logger.debug(
                    "Podcast already exists",
                    method=self.create.__name__,
                    season=self.season,
                    episode=self.episode,
                    part=self.part,
                    date=self.date,
                )
            else:
                self.logger.error(
                    "Failed to create podcast",
                    method=self.create.__name__,
                    season=self.season,
                    episode=self.episode,
                    part=self.part,
                    date=self.date,
                )
                raise RuntimeError()
            data = records[0].data().get("p", {})
            self.uuid = data.get("uuid", "")
            self.created = data.get("created", "")
            self.last_modified = data.get("last_modified", "")
        except Exception as e:
            self.logger.error("Error creating podcast", method=self.create.__name__, error=str(e))
            raise e

    @classmethod
    def find(cls, driver: Driver, uuid: str):
        try:
            records, _, _ = driver.execute_query(
                "MATCH (p:Podcast {uuid: $uuid}) RETURN p",
                uuid=uuid,
                database_=cls.db,
            )
            if records:
                data = records[0].data().get("p", {})
                return cls(
                    driver=driver,
                    season=data.get("season", 0),
                    episode=data.get("episode", 0),
                    part=data.get("part", 0),
                    date=datetime.strptime(data.get("date", ""), "%Y-%m-%d").date(),
                )
            return None
        except Exception as e:
            logger.error("Error finding podcast", method=cls.find.__name__, error=str(e))
            raise e

    @classmethod
    def findall(cls, driver: Driver):
        try:
            records, _, _ = driver.execute_query(
                "MATCH (p:Podcast) RETURN p",
                database_=cls.db,
            )
            podcasts = []
            for record in records:
                data = record.data().get("p", {})
                podcasts.append(
                    cls(
                        driver=driver,
                        season=data.get("season", 0),
                        episode=data.get("episode", 0),
                        part=data.get("part", 0),
                        date=datetime.strptime(data.get("date", ""), "%Y-%m-%d").date(),
                    )
                )
            return podcasts
        except Exception as e:
            logger.error("Error finding all podcasts", method=cls.findall.__name__, error=str(e))
            raise e

    def relate(self, driver: Driver, relationship: str, to_node_label: str, to_node_uuid: str, properties: dict = None):
        try:
            self.verify_connection()
            query = f"""
            MATCH (a:Podcast {{uuid: $from_uuid}}), (b:{to_node_label} {{uuid: $to_uuid}})
            MERGE (a)-[r:{relationship}]->(b)
            ON CREATE SET r += $props
            RETURN r
            """
            self.driver.execute_query(
                query,
                from_uuid=self.uuid,
                to_uuid=to_node_uuid,
                props=properties or {},
                database_=self.db,
            )
            self.logger.debug(
                "Created relationship",
                method=self.relate.__name__,
                from_uuid=self.uuid,
                to_uuid=to_node_uuid,
                relationship=relationship,
            )
        except Exception as e:
            self.logger.error("Error creating relationship", method=self.relate.__name__, error=str(e))
            raise e
