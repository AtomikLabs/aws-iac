#!/bin/bash

LOCK_FILE=/data/.docker_op_complete
if [ -f $LOCK_FILE ]; then
    aws s3 cp s3://$ATOMIKLABS_INFRA_CONFIG_BUCKET_NAME/orchestration/$ATOMIKLABS_ENV/airflow /data/airflow --recursive
    aws s3 cp s3://$ATOMIKLABS_INFRA_CONFIG_BUCKET_NAME/orchestration/$ATOMIKLABS_ENV/airflow/dag/.env /data/airflow/dag/.env
fi