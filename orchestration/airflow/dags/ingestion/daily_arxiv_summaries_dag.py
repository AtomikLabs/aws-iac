from logging.config import dictConfig

import ingestion.tasks.most_recent_research_task as most_recent_research_task
import structlog
from airflow import DAG
from airflow.operators.python import PythonOperator
from shared.utils.constants import DEFAULT_LOGGING_ARGS, LOGGING_CONFIG

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

SERVICE_NAME = "daily_arxiv_summaries_dag"

with DAG(
    SERVICE_NAME,
    default_args=DEFAULT_LOGGING_ARGS,
    schedule_interval=None,
    description="Ingests arXiv summaries every day",
) as dag:

    most_recent_research_task = PythonOperator(
        task_id="most_recent_research",
        python_callable=most_recent_research_task.run,
    )

    fetch_from_arxiv_task = PythonOperator(
        task_id="fetch_from_arxiv",
        python_callable=lambda: logger.info("Fetching data from arXiv"),
    )

most_recent_research_task