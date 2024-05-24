import os
from logging.config import dictConfig

import publishing.tasks.create_pod as cpt
import structlog
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from dotenv import load_dotenv
from shared.utils.constants import (
    AIRFLOW_DAGS_ENV_PATH,
    CREATE_POD_TASK,
    CREATE_PODS_DAG,
    DEFAULT_LOGGING_ARGS,
    LOGGING_CONFIG,
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
SERVICE_NAME = CREATE_PODS_DAG

with DAG(
    SERVICE_NAME,
    catchup=False,
    default_args=DEFAULT_LOGGING_ARGS,
    schedule_interval="0 13 * * *",
    start_date=start_date,
    tags=["process", "arxiv"],
) as dag:
    create_pod_cl = PythonOperator(
        task_id=CREATE_POD_TASK.join("_cl"),
        op_kwargs={"arxiv_set": "CS", "category": "CL"},
        python_callable=cpt.run,
    )

    create_pod_cv = PythonOperator(
        task_id=CREATE_POD_TASK.join("_cv"),
        op_kwargs={"arxiv_set": "CS", "category": "CV"},
        python_callable=cpt.run,
    )

    create_pod_ro = PythonOperator(
        task_id=CREATE_POD_TASK.join("_ro"),
        op_kwargs={"arxiv_set": "CS", "category": "RO"},
        python_callable=cpt.run,
    )

create_pod_cl >> create_pod_cv >> create_pod_ro
