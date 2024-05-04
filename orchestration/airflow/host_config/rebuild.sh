#!/bin/bash

/data/airflow/host_config/sync_s3.sh
cd /data/airflow
docker compose -f docker-compose.yml down
docker compose -f docker-compose.yaml up -d --build
