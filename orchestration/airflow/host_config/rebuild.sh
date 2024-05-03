#!/bin/bash

LOCK_FILE=/data/.docker_op_complete
if [ -f $LOCK_FILE ]; then
    /data/airflow/host_config/sync_s3.sh
    cd /data/airflow/host_config
    docker compose -f docker-compose.yml down
    docker compose -f docker-compose.yaml up -d --build
fi