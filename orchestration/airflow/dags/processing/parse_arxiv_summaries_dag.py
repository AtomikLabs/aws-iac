import os
from logging.config import dictConfig

import processing.tasks.parse_summaries_task as pst
import processing.tasks.persist_summaries_task as psat
import structlog
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from dotenv import load_dotenv
from shared.sensors.kafka_topic_sensor import KafkaTopicSensor
from shared.utils.constants import (
    AIRFLOW_DAGS_ENV_PATH,
    ARXIV_RESEARCH_INGESTION_EVENT_SCHEMA_ENV,
    DATA_ARXIV_SUMMARIES_INGESTION_COMPLETE_TOPIC,
    DEFAULT_LOGGING_ARGS,
    FETCH_FROM_ARXIV_TASK,
    KAFKA_LISTENER,
    LOGGING_CONFIG,
    ORCHESTRATION_HOST_PRIVATE_IP,
    PARSE_ARXIV_SUMMARIES_DAG,
    PARSE_SUMMARIES_TASK,
    PERSIST_SUMMARIES_TASK,
)

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
start_date = days_ago(1)
load_dotenv(dotenv_path=os.getenv(AIRFLOW_DAGS_ENV_PATH))
SERVICE_NAME = PARSE_ARXIV_SUMMARIES_DAG


with DAG(
    SERVICE_NAME,
    catchup=False,
    default_args=DEFAULT_LOGGING_ARGS,
    schedule_interval="0 12 * * *",
    start_date=start_date,
    tags=["process", "arxiv"],
) as dag:

    kafka_listener_task = KafkaTopicSensor(
        task_id=KAFKA_LISTENER,
        topic=DATA_ARXIV_SUMMARIES_INGESTION_COMPLETE_TOPIC,
        schema=os.getenv(ARXIV_RESEARCH_INGESTION_EVENT_SCHEMA_ENV),
        task_ids=[FETCH_FROM_ARXIV_TASK],
        bootstrap_servers=f"{os.getenv(ORCHESTRATION_HOST_PRIVATE_IP)}:9092",
        logger=logger,
        poke_interval=60,
        timeout=360,
        dag=dag,
    )

    parse_summaries_task = PythonOperator(
        task_id=PARSE_SUMMARIES_TASK,
        python_callable=pst.run,
        dag=dag,
        provide_context=True,
    )

    persist_summaries_task = PythonOperator(
        task_id=PERSIST_SUMMARIES_TASK,
        python_callable=psat.run,
        dag=dag,
        provide_context=True,
    )

    kafka_listener_task >> parse_summaries_task
    parse_summaries_task >> persist_summaries_task
