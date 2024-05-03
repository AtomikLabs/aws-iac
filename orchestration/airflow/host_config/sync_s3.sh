#!/bin/bash
sudo aws s3 cp s3://$ATOMIKLABS_INFRA_CONFIG_BUCKET_NAME/orchestration/$ATOMIKLABS_ENV/airflow /data/airflow --recursive