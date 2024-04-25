from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "airflow",
    "start_date": datetime(2024, 4, 24),
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "aws_services_test_dag",
    default_args=default_args,
    description="A simple DAG to test AWS CLI access",
    schedule_interval=None,
)

test_aws_cli = BashOperator(
    task_id="aws_services_test_dag_command",
    bash_command="aws s3 ls s3://dev-atomiklabs-data-bucket/",
    dag=dag,
)

test_aws_cli
