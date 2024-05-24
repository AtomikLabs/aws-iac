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

    FIELDS_CSV = "season|episode|episode_date|uuid|created|last_modified|script_key|audio_key\n"
    LABEL = "Podcast"

    def __init__(
        self,
        driver: Driver = None,
        title: str = "",
        season: int = 0,
        episode: int = 0,
        part=0,
        episode_date: date = None,
        script_key: str = "",
        audio_key: str = "",
    ):
        super().__init__(driver)
        if not title:
            message = "title is required"
            self.logger.error(message, method=self.__init__.__name__)
            raise ValueError(message)
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
        if not script_key:
            message = "script_key is required"
            self.logger.error(message, method=self.__init__.__name__)
            raise ValueError(message)
        if not audio_key:
            message = "audio_key is required"
            self.logger.error(message, method=self.__init__.__name__)
            raise ValueError(message)
        self.title = title
        self.season = season
        self.episode = episode
        self.part = part
        self.episode_date = episode_date
        self.script_key = script_key
        self.audio_key = audio_key
        self.uuid = None
        self.created = None
        self.last_modified = None

    def create(
        self,
        title: str = None,
        season: int = None,
        episode: int = None,
        part: int = None,
        episode_date: date = None,
        script_key: str = None,
        audio_key: str = None,
    ):
        title = title if title is not None else self.title
        season = season if season is not None else self.season
        episode = episode if episode is not None else self.episode
        part = part if part is not None else self.part
        episode_date = episode_date if episode_date is not None else self.episode_date
        script_key = script_key if script_key is not None else self.script_key
        audio_key = audio_key if audio_key is not None else self.audio_key

        if (
            title is None
            or season is None
            or episode is None
            or episode_date is None
            or not script_key
            or not audio_key
        ):
            message = "title, season, episode, episode_date, script_key, and audio_key are required for creation"
            self.logger.error(message, method=self.create.__name__)
            raise ValueError(message)
        if not isinstance(title, str):
            message = "title must be a string"
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
            self.title = title
            self.season = season
            self.episode = episode
            self.part = part
            self.episode_date = episode_date
            self.script_key = script_key
            self.audio_key = audio_key
            self.verify_connection()
            self.logger.debug(
                "Creating Podcast",
                method=self.create.__name__,
                title=self.title,
                season=self.season,
                episode=self.episode,
                part=self.part,
                episode_date=self.episode_date,
                script_key=self.script_key,
                audio_key=self.audio_key,
            )
            now = get_storage_key_datetime()
            self.uuid = str(uuid.uuid4())
            query = """
                CREATE (p:Podcast {
                    uuid: $uuid,
                    title: $title,
                    season: $season,
                    episode: $episode,
                    part: $part,
                    episode_date: $episode_date,
                    script_key: $script_key,
                    audio_key: $audio_key,
                    created_at: $created_at
                })
            """
            parameters = {
                "uuid": self.uuid,
                "title": self.title,
                "season": self.season,
                "episode": self.episode,
                "part": self.part,
                "episode_date": self.episode_date,
                "script_key": self.script_key,
                "audio_key": self.audio_key,
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
                    title=data.get("title", ""),
                    season=data.get("season", 0),
                    episode=data.get("episode", 0),
                    part=data.get("part", 0),
                    episode_date=data.get("episode_date", ""),
                    script_key=data.get("script_key", ""),
                    audio_key=data.get("audio_key", ""),
                )
                podcast.created = data.get("created", "")
                podcast.last_modified = data.get("last_modified", "")
                return podcast
            return None
        except Exception as e:
            logger.error("Error finding podcast", method=cls.find.__name__, error=str(e))
            raise e

    @classmethod
    def find_all(cls, driver: Driver):
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
                    title=data.get("title", ""),
                    season=data.get("season", 0),
                    episode=data.get("episode", 0),
                    part=data.get("part", 0),
                    episode_date=data.get("episode_date", ""),
                    script_key=data.get("script_key", ""),
                    audio_key=data.get("audio_key", ""),
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
