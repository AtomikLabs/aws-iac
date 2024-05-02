#!/bin/bash

echo "Starting the volume setup script..." >> /home/ec2-user/init.log

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
        echo "Waiting for volume ID..." >> /home/ec2-user/init.log
    fi
done

if [[ -z $VOLUME_ID ]]; then
    echo "Failed to fetch VOLUME_ID within the timeout period." >> /home/ec2-user/init.log
    exit 1
fi

echo "VOLUME_ID: $VOLUME_ID" >> /home/ec2-user/init.log

DEVICE_NAME=""
ELAPSED=0
while [[ -z $DEVICE_NAME && $ELAPSED -lt $TIMEOUT ]]; do
    DEVICE_NAME=$(lsblk -d -no NAME,SERIAL | awk -v sn="$VOLUME_ID" '$2 == sn {print "/dev/" $1}')
    if [[ -z $DEVICE_NAME ]]; then
        sleep $INTERVAL
        ELAPSED=$((ELAPSED + INTERVAL))
        echo "Waiting for device to attach..." >> /home/ec2-user/init.log
    fi
done

if [[ -z $DEVICE_NAME ]]; then
    echo "Failed to identify the device within the timeout period." >> /home/ec2-user/init.log
    exit 1
fi

echo "DEVICE_NAME: $DEVICE_NAME" >> /home/ec2-user/init.log

FILETYPE=$(sudo file -s $DEVICE_NAME)
echo "File system type: $FILETYPE" >> /home/ec2-user/init.log
if [[ $FILETYPE == *": data"* ]]; then
    echo "Formatting device $DEVICE_NAME" >> /home/ec2-user/init.log
    sudo mkfs -t ext4 $DEVICE_NAME
else
    echo "Device $DEVICE_NAME is already formatted. Checking filesystem." >> /home/ec2-user/init.log
    sudo e2fsck -p -f $DEVICE_NAME
fi

grep -q "$DEVICE_NAME" /etc/fstab || echo "$DEVICE_NAME /data ext4 defaults,nofail 0 2" | sudo tee -a /etc/fstab
cat /etc/fstab >> /home/ec2-user/init.log
lsblk >> /home/ec2-user/init.log
sleep 15
mount -a
lsblk >> /home/ec2-user/init.log

if mount | grep -q /data; then
    echo "/data mounted successfully." >> /home/ec2-user/init.log
else
    echo "Failed to mount /data, retrying..." >> /home/ec2-user/init.log
    mount -av >> /home/ec2-user/init.log 2>&1
fi

echo "Volume setup script completed." >> /home/ec2-user/init.log

echo "Starting Python setup script..." >> /home/ec2-user/init.log

yum install -y pip3

echo "Python setup script completed." >> /home/ec2-user/init.log

echo "Starting the kafka setup script..." >> /home/ec2-user/init.log

mkdir -p /data/kafka/logs
mkdir -p /data/kafka/kafka-ui
mkdir -p /data/kafka
chown -R 1000:1000 /data/kafka
chmod -R 755 /data/kafka

cat << 'EOF' > /data/kafka/sync_s3.sh
#!/bin/bash
sudo aws s3 sync s3://${infra_bucket_name}/orchestration/${environment}/kafka /data/kafka
EOF

cd /data/kafka
chmod +x /data/kafka/sync_s3.sh
/data/kafka/sync_s3.sh
yum install -y pip3
python3 -m venv .venv
source .venv/bin/activate
pip install -r /data/kafka/requirements.txt
python3 /data/kafka/create_topics.py
deactivate

echo "Kafka setup script completed." >> /home/ec2-user/init.log

echo "Starting the airflow setup script..." >> /home/ec2-user/init.log

mkdir -p /data/airflow/dags /data/airflow/logs /data/airflow/plugins /data/airflow/config
chown -R 50000:50000 /data/airflow
chmod -R 755 /data/airflow
cd /data/airflow

echo -e "AIRFLOW_UID=$(id -u)\nAIRFLOW_GID=0" > /data/.env

cat << 'EOF' > /data/airflow/sync_s3.sh
#!/bin/bash
sudo aws s3 sync s3://${infra_bucket_name}/orchestration/${environment}/airflow/dags /data/airflow/dags
sudo aws s3 sync s3://${infra_bucket_name}/orchestration/${environment}/airflow/plugins /data/airflow/plugins
sudo aws s3 sync s3://${infra_bucket_name}/orchestration/${environment}/airflow/config /data/airflow/config
sudo aws s3 cp s3://${infra_bucket_name}/orchestration/${environment}/airflow/Dockerfile /data/airflow/Dockerfile
sudo aws s3 cp s3://${infra_bucket_name}/orchestration/${environment}/airflow/docker-compose.yaml /data/airflow/docker-compose.yaml
sudo aws s3 cp s3://${infra_bucket_name}/orchestration/${environment}/airflow/requirements.txt /data/airflow/requirements.txt
EOF

chmod +x /data/airflow/sync_s3.sh
/data/airflow/sync_s3.sh

mkdir /etc/docker
echo "Configuring docker" >> /home/ec2-user/init.log
echo '{
  "data-root": "/data/docker"
}' > /etc/docker/daemon.json

echo "Installing docker" >> /home/ec2-user/init.log
yum update -y
yum install docker -y
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

echo "Installing docker-compose" >> /home/ec2-user/init.log
DOCKER_CONFIG=/usr/local/lib/docker/cli-plugins
mkdir -p $DOCKER_CONFIG
curl -SL https://github.com/docker/compose/releases/download/v2.26.1/docker-compose-linux-x86_64 -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x $DOCKER_CONFIG/docker-compose

echo "Airflow setup script completed." >> /home/ec2-user/init.log

echo "Building and starting Docker" >> /home/ec2-user/init.log
docker compose -f /data/airflow/docker-compose.yaml up airflow-init
docker compose -f /data/airflow/docker-compose.yaml --profile flower up -d

