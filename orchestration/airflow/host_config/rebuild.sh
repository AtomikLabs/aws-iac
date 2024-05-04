#!/bin/bash

aws s3 cp s3://$ATOMIKLABS_INFRA_BUCKET_NAME/orchestration/$ATOMIKLABS_ENV/airflow /data/airflow --recursive
aws s3 cp s3://$ATOMIKLABS_INFRA_BUCKET_NAME/orchestration/$ATOMIKLABS_ENV/airflow/dags/.env /data/airflow/dags/.env

/data/airflow/host_config/sync_s3.sh
cd /data/airflow/host_config
docker compose -f docker-compose.yml down
docker compose -f docker-compose.yaml up -d --build
