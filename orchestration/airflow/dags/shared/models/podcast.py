import logging
import uuid
from datetime import date

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

    FIELDS_CSV = "season|episode|episode_date|uuid|created|last_modified|script_url|audio_url\n"
    LABEL = "Podcast"

    def __init__(
        self,
        driver: Driver = None,
        season: int = 0,
        episode: int = 0,
        part=0,
        episode_date: date = None,
        script_url: str = "",
        audio_url: str = "",
    ):
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
        if episode_date and not isinstance(episode_date, date):
            message = "episode_date must be a valid date object"
            self.logger.error(message, method=self.__init__.__name__)
            raise ValueError(message)
        if not script_url:
            message = "script_url is required"
            self.logger.error(message, method=self.__init__.__name__)
            raise ValueError(message)
        if not audio_url:
            message = "audio_url is required"
            self.logger.error(message, method=self.__init__.__name__)
            raise ValueError(message)
        self.season = season
        self.episode = episode
        self.part = part
        self.episode_date = episode_date
        self.script_url = script_url
        self.audio_url = audio_url
        self.uuid = None
        self.created = None
        self.last_modified = None

    def create(
        self,
        season: int = None,
        episode: int = None,
        part: int = None,
        episode_date: date = None,
        script_url: str = None,
        audio_url: str = None,
    ):
        season = season if season is not None else self.season
        episode = episode if episode is not None else self.episode
        part = part if part is not None else self.part
        episode_date = episode_date if episode_date is not None else self.episode_date
        script_url = script_url if script_url is not None else self.script_url
        audio_url = audio_url if audio_url is not None else self.audio_url

        if season is None or episode is None or episode_date is None or not script_url or not audio_url:
            message = "season, episode, episode_date, script_url, and audio_url are required for creation"
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
        if not isinstance(episode_date, date):
            message = "episode_date must be a valid date object"
            self.logger.error(message, method=self.create.__name__)
            raise ValueError(message)

        try:
            self.season = season
            self.episode = episode
            self.part = part
            self.episode_date = episode_date
            self.script_url = script_url
            self.audio_url = audio_url
            self.verify_connection()
            self.logger.debug(
                "Creating Podcast",
                method=self.create.__name__,
                season=self.season,
                episode=self.episode,
                part=self.part,
                episode_date=self.episode_date,
                script_url=self.script_url,
                audio_url=self.audio_url,
            )
            now = get_storage_key_datetime()
            self.uuid = str(uuid.uuid4())
            query = """
                CREATE (p:Podcast {
                    uuid: $uuid,
                    season: $season,
                    episode: $episode,
                    part: $part,
                    episode_date: $episode_date,
                    script_url: $script_url,
                    audio_url: $audio_url,
                    created_at: $created_at
                })
            """
            parameters = {
                "uuid": self.uuid,
                "season": self.season,
                "episode": self.episode,
                "part": self.part,
                "episode_date": self.episode_date,
                "script_url": self.script_url,
                "audio_url": self.audio_url,
                "created": now,
                "last_modified": now,
            }
            self.execute_query(query, parameters)
        except Exception as e:
            self.logger.error(f"Failed to create podcast: {e}", method=self.create.__name__)
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
                podcast = cls(
                    driver=driver,
                    season=data.get("season", 0),
                    episode=data.get("episode", 0),
                    part=data.get("part", 0),
                    episode_date=data.get("episode_date", ""),
                    script_url=data.get("script_url", ""),
                    audio_url=data.get("audio_url", ""),
                )
                podcast.created = data.get("created", "")
                podcast.last_modified = data.get("last_modified", "")
                return podcast
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
                podcast = cls(
                    driver=driver,
                    season=data.get("season", 0),
                    episode=data.get("episode", 0),
                    part=data.get("part", 0),
                    episode_date=data.get("episode_date", ""),
                    script_url=data.get("script_url", ""),
                    audio_url=data.get("audio_url", ""),
                )
                podcast.created = data.get("created", "")
                podcast.last_modified = data.get("last_modified", "")
                podcasts.append(podcast)
            return podcasts
        except Exception as e:
            logger.error("Error finding all podcasts", method=cls.findall.__name__, error=str(e))
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
