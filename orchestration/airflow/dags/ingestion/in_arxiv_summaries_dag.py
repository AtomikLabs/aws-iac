from datetime import datetime

import structlog

from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from logging.config import dictConfig

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'plain': {
            '()': 'airflow.utils.log.logging_mixin.RedirectStdHandler',
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'plain',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    }
}

dictConfig(LOGGING_CONFIG)

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': '2024-04-25',
    'retries': 1,
}

with DAG('in_arxiv_summaries_dag',
         default_args=default_args,
         schedule_interval=None,
         start_date=datetime(2024, 4, 25),
         description="A test ingest DAG") as dag:

    ingest = PythonOperator(
        task_id="ingest",
        python_callable=lambda: logger.info("Ingesting data"),
    )

    ingest
