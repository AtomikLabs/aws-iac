#!/bin/bash

aws s3 cp s3://$ATOMIKLABS_INFRA_BUCKET_NAME/orchestration/$ATOMIKLABS_ENV/kafka /data/kafka --recursive
aws s3 cp s3://$ATOMIKLABS_INFRA_BUCKET_NAME/orchestration/$ATOMIKLABS_ENV/kafka/.env /data/kafka/.env

/data/kafka/host_config/sync_s3.sh
cd /data/kafka/host_config
docker compose -f docker-compose.yml down
docker compose -f docker-compose.yaml up -d --build
docker compose -f docker-compose.yaml run --rm --no-deps --entrypoint '/bin/sh' broker -c 'start=$(date +%s); while : ; do /opt/kafka/bin/kafka-topics.sh --bootstrap-server $KAFKA_IP:9092 --list > /dev/null 2>&1; [ $? -eq 0 ] && break; now=$(date +%s); [ $((now - start)) -ge 900 ] && break; sleep 5; done'
/data/kafka/host_config/update_topics.sh
