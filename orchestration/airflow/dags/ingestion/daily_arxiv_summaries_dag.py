from logging.config import dictConfig

import ingestion.tasks.fetch_from_arxiv_task as ffat
import ingestion.tasks.most_recent_research_task as mrrt
import structlog
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import cron_datetime, days_ago
from pendulum import timezone
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

start_date = days_ago(1)

PST = timezone("US/Pacific")

daily_schedule = cron_datetime(hour=4, minute=0, tz=PST)

with DAG(
    SERVICE_NAME,
    catchup=False,
    default_args=DEFAULT_LOGGING_ARGS,
    schedule_interval=daily_schedule,
    tags=["ingestion"],
) as dag:

    most_recent_research_task = PythonOperator(
        task_id="most_recent_research",
        python_callable=mrrt.run,
        dag=dag,
        provide_context=True,
    )

    fetch_from_arxiv_task = PythonOperator(
        task_id="fetch_from_arxiv",
        python_callable=ffat.run,
        dag=dag,
        provide_context=True,
    )

    most_recent_research_task >> fetch_from_arxiv_task
