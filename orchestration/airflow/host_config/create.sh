#!/bin/sh

aws s3 cp s3://$ATOMIKLABS_INFRA_BUCKET_NAME/orchestration/$ATOMIKLABS_ENV/airflow /data/airflow --recursive
aws s3 cp s3://$ATOMIKLABS_INFRA_BUCKET_NAME/orchestration/$ATOMIKLABS_ENV/airflow/dags/.env /data/airflow/dags/.env

echo "Starting Airflow setup..." 

sudo mkdir -p /data/airflow/dags /data/airflow/logs /data/airflow/plugins /data/airflow/config
sudo chown -R 50000:50000 /data/airflow
sudo chmod -R 755 /data/airflow

echo -e "AIRFLOW_UID=$(id -u)\nAIRFLOW_GID=0" > /data/.env

echo "Building and starting Airflow" 
docker compose -f /data/airflow/host_config/docker-compose.yaml up -d --build

echo "Airflow setup completed." 
