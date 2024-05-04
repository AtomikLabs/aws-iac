#!/bin/bash

aws s3 cp s3://$ATOMIKLABS_INFRA_BUCKET_NAME/orchestration/$ATOMIKLABS_ENV/kafka /data/kafka --recursive
aws s3 cp s3://$ATOMIKLABS_INFRA_BUCKET_NAME/orchestration/$ATOMIKLABS_ENV/kafka/.env /data/kafka/.env

echo "Starting Kafka setup..." 

mkdir -p /data/kafka/logs
mkdir -p /data/kafka/kafka-ui
mkdir -p /data/kafka/topics
mkdir -p /data/kafka/host_config
chown -R 1000:1000 /data/kafka
chmod -R 755 /data/kafka

echo "Building and starting Kafka" 
cd /data/kafka/host_config
docker compose -f docker-compose.yaml up -d --build
docker compose -f docker-compose.yaml run --rm --no-deps --entrypoint '/bin/sh' broker -c 'start=$(date +%s); while : ; do /opt/kafka/bin/kafka-topics.sh --bootstrap-server $KAFKA_IP:9092 --list > /dev/null 2>&1; [ $? -eq 0 ] && break; now=$(date +%s); [ $((now - start)) -ge 900 ] && break; sleep 5; done'

cd /data/kafka/topics
yum install -y pip
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 create_topics.py
deactivate

echo "Kafka setup completed." 
