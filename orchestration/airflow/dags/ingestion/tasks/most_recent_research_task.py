import os
from datetime import timedelta
from logging.config import dictConfig

from dotenv import load_dotenv
import structlog
from shared.utils.constants import (
    LOGGING_CONFIG,
)
from shared.utils.utils import get_storage_key_datetime

dictConfig(LOGGING_CONFIG)

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()
load_dotenv(dotenv_path="/opt/airflow/dags/.env")

TASK_NAME = "most_recent_research"


def run(**context: dict):
    logger.info(
        f"Running {TASK_NAME} task", task_name=TASK_NAME, date=context["execution_date"], run_id=context["run_id"]
    )
    earliest_date = get_storage_key_datetime() - timedelta(days=os.getenv("ARXIV_INGESTION_DAY_SPAN", 1))
    logger.info(f"Earliest date to fetch data from: {earliest_date}")
    logger.info(f"dev: {os.getenv('ENV')}")
