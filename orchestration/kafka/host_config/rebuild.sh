#!/bin/bash

cd /data/kafka
docker compose -f /data/kafka/host_config/docker-compose.yml down
docker compose -f /data/kafka/host_config/docker-compose.yaml up -d --build
docker compose -f /data/kafka/host_config/docker-compose.yaml run --rm --no-deps --entrypoint '/bin/sh' broker -c 'start=$(date +%s); while : ; do /opt/kafka/bin/kafka-topics.sh --bootstrap-server $KAFKA_IP:9092 --list > /dev/null 2>&1; [ $? -eq 0 ] && break; now=$(date +%s); [ $((now - start)) -ge 900 ] && break; sleep 5; done'

