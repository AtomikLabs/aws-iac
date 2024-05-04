#!/bin/bash

exec > /home/ec2-user/init.log 2>&1

echo "Starting the volume setup..."

TIMEOUT=300  # 5 minutes
INTERVAL=10  # 10 seconds
ELAPSED=0
VOLUME_ID=""

mkdir /data
chmod 777 -R /data

while [[ -z $VOLUME_ID && $ELAPSED -lt $TIMEOUT ]]; do
    VOLUME_ID=$(aws ec2 describe-volumes --filters "Name=tag:Name,Values=${volume_name_tag}" --query "Volumes[*].VolumeId" --output text)
    VOLUME_ID=$${VOLUME_ID//-/}
    if [[ -z $VOLUME_ID ]]; then
        sleep $INTERVAL
        ELAPSED=$((ELAPSED + INTERVAL))
        echo "Waiting for volume ID..."
    fi
done

if [[ -z $VOLUME_ID ]]; then
    echo "Failed to fetch VOLUME_ID within the timeout period." 
    exit 1
fi

echo "VOLUME_ID: $VOLUME_ID" 

DEVICE_NAME=""
ELAPSED=0
while [[ -z $DEVICE_NAME && $ELAPSED -lt $TIMEOUT ]]; do
    DEVICE_NAME=$(lsblk -d -no NAME,SERIAL | awk -v sn="$VOLUME_ID" '$2 == sn {print "/dev/" $1}')
    if [[ -z $DEVICE_NAME ]]; then
        sleep $INTERVAL
        ELAPSED=$((ELAPSED + INTERVAL))
        echo "Waiting for device to attach..." 
    fi
done

if [[ -z $DEVICE_NAME ]]; then
    echo "Failed to identify the device within the timeout period." 
    exit 1
fi

echo "DEVICE_NAME: $DEVICE_NAME" 

FILETYPE=$(sudo file -s $DEVICE_NAME)
echo "File system type: $FILETYPE" 
if [[ $FILETYPE == *": data"* ]]; then
    echo "Formatting device $DEVICE_NAME" 
    sudo mkfs -t ext4 $DEVICE_NAME
else
    echo "Device $DEVICE_NAME is already formatted. Checking filesystem." 
    sudo e2fsck -p -f $DEVICE_NAME
fi

grep -q "$DEVICE_NAME" /etc/fstab || echo "$DEVICE_NAME /data ext4 defaults,nofail 0 2" | sudo tee -a /etc/fstab
cat /etc/fstab 
lsblk 
sleep 15
mount -a
lsblk 

if mount | grep -q /data; then
    echo "/data mounted successfully." 
else
    echo "Failed to mount /data, retrying..." 
    mount -av
fi

echo "Volume setup completed." 

echo "Starting Python setup..." 

yum install -y pip

echo "Python setup completed." 

echo "Starting environment setup..." 

echo "ATOMIKLABS_INFRA_BUCKET_NAME=${infra_bucket_name}" >> /etc/environment
echo "ATOMIKLABS_ENV=${environment}" >> /etc/environment
source /etc/environment
cat /etc/environment 

echo "Environment setup completed." 

echo "Starting Docker setup..." 

mkdir /etc/docker
echo "Configuring Docker" 
echo '{
  "data-root": "/data/docker"
}' > /etc/docker/daemon.json

echo "Installing Docker" 
yum update -y
yum install docker -y
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

echo "Installing docker-compose" 
DOCKER_CONFIG=/usr/local/lib/docker/cli-plugins
mkdir -p $DOCKER_CONFIG
curl -SL https://github.com/docker/compose/releases/download/v2.26.1/docker-compose-linux-x86_64 -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x $DOCKER_CONFIG/docker-compose

echo "Docker setup completed." 

echo "Starting the Airflow setup..." 

sudo mkdir -p /data/airflow/dags /data/airflow/logs /data/airflow/plugins /data/airflow/config
sudo chown -R 50000:50000 /data/airflow
sudo chmod -R 755 /data/airflow

echo -e "AIRFLOW_UID=$(id -u)\nAIRFLOW_GID=0" > /data/.env

aws s3 cp s3://$ATOMIKLABS_INFRA_BUCKET_NAME/orchestration/$ATOMIKLABS_ENV/airflow /data/airflow --recursive

echo "Building and starting Airflow" 
docker compose -f /data/airflow/host_config/docker-compose.yaml up -d --build

echo "Airflow setup completed." 

echo "Starting Kafka setup..." 

mkdir -p /data/kafka/logs
mkdir -p /data/kafka/kafka-ui
mkdir -p /data/kafka/topics
mkdir -p /data/kafka/host_config
chown -R 1000:1000 /data/kafka
chmod -R 755 /data/kafka

aws s3 cp s3://$ATOMIKLABS_INFRA_BUCKET_NAME/orchestration/$ATOMIKLABS_ENV/kafka /data/kafka --recursive

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

touch /data/.docker_op_complete