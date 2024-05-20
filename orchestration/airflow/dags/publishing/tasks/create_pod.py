from datetime import date, datetime, timedelta
from logging.config import dictConfig
from typing import Dict, List

import structlog
from dotenv import load_dotenv
from neo4j import GraphDatabase
from shared.utils.constants import (
    AIRFLOW_DAGS_ENV_PATH,
    AWS_REGION,
    CATEGORIZED_BY,
    CATEGORIZES,
    ENVIRONMENT_NAME,
    LOGGING_CONFIG,
)
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
        env_vars = [AWS_REGION, ENVIRONMENT_NAME]
        config = get_config(context, env_vars, True)
        next_date = last_pod_date(config, arxiv_set, category)
        if not next_date:
            logger.info("Podcasts up to date", set=arxiv_set, category=category, method=last_pod_date.__name__)
            return {"statusCode": 200, "body": "Podcasts up to date"}
        next_date = next_date + timedelta(days=1)
        date_list = [next_date + timedelta(days=i) for i in range((datetime.now() - next_date).days)]
        if not date_list:
            logger.info("No dates require podcasts", set=arxiv_set, category=category, date_list=date_list)
            return {"statusCode": 200, "body": "No dates require podcasts", "date_list": date_list}
        logger.info("Date list", date_list=date_list)
        for pod_date in date_list:
            logger.info("Creating pod", set=arxiv_set, category=category, date=pod_date)
            summaries = get_summaries(config, arxiv_set, category, pod_date)
            if not summaries:
                logger.info("No summaries for date", set=arxiv_set, category=category, date=pod_date)
                continue
            pod_summaries = get_pod_summaries(summaries)
            pod_scripts = get_pod_scripts(pod_summaries, arxiv_set, category, pod_date)
            generate_pods(config, pod_scripts)
            logger.info("Pod created", set=arxiv_set, category=category, date=pod_date)
        return {"statusCode": 200, "body": "Pod created", "date_list": date_list}
    except Exception as e:
        logger.error("Error creating pod", set=arxiv_set, category=category, error=e)
        return {"statusCode": 500, "body": "Error creating pod"}


def last_pod_date(config: dict, arxiv_set: str, category: str) -> date:
    logger.info("Getting last pod date")
    try:
        driver = GraphDatabase.driver(config["NEO4J_URI"], auth=(config["NEO4J_USERNAME"], config["NEO4J_PASSWORD"]))
        with driver.session() as session:
            query = (
                f"MATCH (a:ArxivSet {{code: $arxiv_set}})-[:{CATEGORIZED_BY}]->(c:ArxivCategory {{code: $category}})"
                f"-[:{CATEGORIZES}]->(p:PodCast) "
                "RETURN p.date ORDER BY p.date DESC LIMIT 1"
            )
            result = session.run(query, {"arxiv_set": arxiv_set, "category": category})
            data = result.data()
            return data[0]["p.date"].to_native() if data else None
    except Exception as e:
        logger.error("Error getting last pod date", error=e)
        raise e


def get_summaries(config: dict, arxiv_set: str, category: str, episode_date: datetime) -> List[Dict[str, str]]:
    logger.info("Getting summaries", set=arxiv_set, category=category, date=episode_date)
    try:
        driver = GraphDatabase.driver(config["NEO4J_URI"], auth=(config["NEO4J_USERNAME"], config["NEO4J_PASSWORD"]))
        with driver.session() as session:
            query = (
                f"MATCH (c:ArxivCategory {{code: $category}})"
                f"-[:{CATEGORIZES}]->(a:ArxivRecord) "
                f"WHERE a.date = $date "
                "RETURN a"
            )
            result = session.run(query, {"arxiv_set": arxiv_set, "category": category, "date": episode_date.date()})
            data = result.data()
            logger.info(data)
            return [r["a"] for r in data]
            return data
    except Exception as e:
        logger.error("Error getting summaries", error=e)
        raise e


def get_pod_summaries(summaries: List[Dict[str, str]]) -> List[Dict[str, str]]:
    logger.info("Getting pod summaries", summaries=summaries)
    # for every ArxivRecord in summaries,
    pass


def get_pod_scripts(
    pod_summaries: List[Dict[str, str]], arxiv_set: str, category: str, date: datetime
) -> List[Dict[str, str]]:
    logger.info("Getting pod scripts", pod_summaries=pod_summaries, set=arxiv_set, category=category, date=date)
    pass


def generate_pods(config: dict, pod_scripts: List[Dict[str, str]]) -> None:
    logger.info("Generating pods", pod_scripts=pod_scripts)
    pass
