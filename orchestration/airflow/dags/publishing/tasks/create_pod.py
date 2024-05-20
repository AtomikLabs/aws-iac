from datetime import datetime, timedelta
from logging.config import dictConfig
from typing import Dict, List

import structlog
from dotenv import load_dotenv
from shared.utils.constants import AIRFLOW_DAGS_ENV_PATH, LOGGING_CONFIG
from shared.utils.utils import get_config

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
load_dotenv(dotenv_path=AIRFLOW_DAGS_ENV_PATH)


def run(
    arxiv_set: str,
    category: str,
    **context: dict,
):
    try:
        logger.info("Creating pod", set=arxiv_set, category=category)
        env_vars = []
        config = get_config(context, env_vars, True)
        next_date = last_pod_date(config) + timedelta(days=1)
        date_list = [next_date + timedelta(days=i) for i in range((datetime.now() - next_date).days)]
        for pod_date in date_list:
            logger.info("Creating pod", set=arxiv_set, category=category, date=pod_date)
            summaries = get_summaries(config, arxiv_set, category, pod_date)
            pod_summaries = get_pod_summaries(summaries)
            pod_scripts = get_pod_scripts(pod_summaries, arxiv_set, category, pod_date)
            generate_pods(config, pod_scripts)
            logger.info("Pod created", set=arxiv_set, category=category, date=pod_date)
        return {"statusCode": 200, "body": "Pod created", "date_list": date_list}
    except Exception as e:
        logger.error("Error creating pod", set=arxiv_set, category=category, error=e)
        return {"statusCode": 500, "body": "Error creating pod"}


def last_pod_date(config: dict) -> datetime:
    logger.info("Getting last pod date")
    pass


def get_summaries(config: dict, arxiv_set: str, category: str, date: datetime) -> List[Dict[str, str]]:
    logger.info("Getting summaries", set=arxiv_set, category=category, date=date)
    pass


def get_pod_summaries(summaries: List[Dict[str, str]]) -> List[Dict[str, str]]:
    logger.info("Getting pod summaries", summaries=summaries)
    pass


def get_pod_scripts(
    pod_summaries: List[Dict[str, str]], arxiv_set: str, category: str, date: datetime
) -> List[Dict[str, str]]:
    logger.info("Getting pod scripts", pod_summaries=pod_summaries, set=arxiv_set, category=category, date=date)
    pass


def generate_pods(config: dict, pod_scripts: List[Dict[str, str]]) -> None:
    logger.info("Generating pods", pod_scripts=pod_scripts)
    pass
