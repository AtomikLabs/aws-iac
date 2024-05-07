from logging.config import dictConfig

import processing.tasks.create_intermediate_json_task as cijt
import processing.tasks.generate_neo4j_graph_task as gngt
import processing.tasks.save_full_text_to_datalake_task as sfdt
import processing.tasks.save_summaries_to_datalake_task as ssdl
import structlog
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from shared.sensors.kafka_topic_sensor import KafkaTopicSensor
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

SERVICE_NAME = "process_arxiv_summaries_dag"

start_date = days_ago(1)

with DAG(
    SERVICE_NAME,
    catchup=False,
    default_args=DEFAULT_LOGGING_ARGS,
    schedule_interval="@hourly",
    start_date=start_date,
    tags=["process", "arxiv"],
) as dag:

    kafka_listener_task = KafkaTopicSensor(
        task_id="kafka_listener",
        topic="arxiv_summaries",
        bootstrap_servers="broker:9092",
        poke_interval=60,
        timeout=600,
        dag=dag,
    )

    create_intermediate_json_task = PythonOperator(
        task_id="create_intermediate_json",
        python_callable=cijt.run,
        dag=dag,
        provide_context=True,
    )

    save_summaries_to_datalake_task = PythonOperator(
        task_id="save_summaries_to_datalake",
        python_callable=ssdl.run,
        dag=dag,
        provide_context=True,
    )

    save_full_text_to_datalake_task = PythonOperator(
        task_id="save_full_text_to_datalake",
        python_callable=sfdt.run,
        dag=dag,
        provide_context=True,
    )

    generate_neo4j_graph_task = PythonOperator(
        task_id="generate_neo4j_nodes",
        python_callable=gngt.run,
        dag=dag,
        provide_context=True,
    )

    kafka_listener_task >> create_intermediate_json_task
    create_intermediate_json_task >> generate_neo4j_graph_task
    generate_neo4j_graph_task >> save_summaries_to_datalake_task
    generate_neo4j_graph_task >> save_full_text_to_datalake_task
