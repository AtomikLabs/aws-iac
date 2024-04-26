#!/bin/bash

echo "Starting the volume setup script..." >> /data/airflow/init.log

TIMEOUT=300  # 5 minutes
INTERVAL=10  # 10 seconds
ELAPSED=0
VOLUME_ID=""

while [[ -z $VOLUME_ID && $ELAPSED -lt $TIMEOUT ]]; do
    VOLUME_ID=$(aws ec2 describe-volumes --filters "Name=tag:Name,Values=${volume_name_tag}" --query "Volumes[*].VolumeId" --output text)
    VOLUME_ID=$${VOLUME_ID//-/}
    if [[ -z $VOLUME_ID ]]; then
        sleep $INTERVAL
        ELAPSED=$((ELAPSED + INTERVAL))
        echo "Waiting for volume ID..." >> /data/airflow/init.log
    fi
done

if [[ -z $VOLUME_ID ]]; then
    echo "Failed to fetch VOLUME_ID within the timeout period." >> /data/airflow/init.log
    exit 1
fi

echo "VOLUME_ID: $VOLUME_ID" >> /data/airflow/init.log

DEVICE_NAME=""
ELAPSED=0
while [[ -z $DEVICE_NAME && $ELAPSED -lt $TIMEOUT ]]; do
    DEVICE_NAME=$(lsblk -d -no NAME,SERIAL | awk -v sn="$VOLUME_ID" '$2 == sn {print "/dev/" $1}')
    if [[ -z $DEVICE_NAME ]]; then
        sleep $INTERVAL
        ELAPSED=$((ELAPSED + INTERVAL))
        echo "Waiting for device to attach..." >> /data/airflow/init.log
    fi
done

if [[ -z $DEVICE_NAME ]]; then
    echo "Failed to identify the device within the timeout period." >> /data/airflow/init.log
    exit 1
fi

echo "DEVICE_NAME: $DEVICE_NAME" >> /data/airflow/init.log

FILETYPE=$(sudo file -s $DEVICE_NAME)
echo "File system type: $FILETYPE" >> /data/airflow/init.log
if [[ $FILETYPE == *": data"* ]]; then
    echo "Formatting device $DEVICE_NAME" >> /data/airflow/init.log
    sudo mkfs -t ext4 $DEVICE_NAME
else
    echo "Device $DEVICE_NAME is already formatted. Checking filesystem." >> /data/airflow/init.log
    sudo e2fsck -p -f $DEVICE_NAME
fi

mkdir -p /data/dags /data/logs /data/plugins /data/config
chown -R ec2-user:ec2-user /data/*

grep -q "$DEVICE_NAME" /etc/fstab || echo "$DEVICE_NAME /data ext4 defaults,nofail 0 2" | sudo tee -a /etc/fstab
cat /etc/fstab >> /data/airflow/init.log
lsblk >> /data/airflow/init.log
sleep 15
mount -a
lsblk >> /data/airflow/init.log

if mount | grep -q /data; then
    echo "/data mounted successfully." >> /data/airflow/init.log
else
    echo "Failed to mount /data, retrying..." >> /data/airflow/init.log
    mount -av >> /data/airflow/init.log 2>&1
fi

cd /data/airflow

echo -e "AIRFLOW_UID=$(id -u)\nAIRFLOW_GID=0" > /data/.env

cat << 'EOF' > /data/airflow/sync_s3.sh
#!/bin/bash
sudo aws s3 sync s3://${infra_bucket_name}/orchestration/airflow/dags /data/airflow/dags
sudo aws s3 sync s3://${infra_bucket_name}/orchestration/airflow/plugins /data/airflow/plugins
sudo aws s3 sync s3://${infra_bucket_name}/orchestration/airflow/config /data/airflow/config
sudo aws s3 cp s3://${infra_bucket_name}/orchestration/airflow/Dockerfile /data/airflow/Dockerfile
sudo aws s3 cp s3://${infra_bucket_name}/orchestration/airflow/docker-compose.yml /data/airflow/docker-compose.yml
sudo aws s3 cp s3://${infra_bucket_name}/orchestration/airflow/requirements.txt /data/airflow/requirements.txt
EOF

chmod +x /data/airflow/sync_s3.sh
/data/airflow/sync_s3.sh

mkdir /etc/docker
echo "Configuring docker" >> /data/airflow/init.log
echo '{
  "data-root": "/data/docker"
}' > /etc/docker/daemon.json

echo "Installing docker" >> /data/airflow/init.log
yum update -y
yum install docker -y
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

echo "Installing docker-compose" >> /data/airflow/init.log
DOCKER_CONFIG=/usr/local/lib/docker/cli-plugins
mkdir -p $DOCKER_CONFIG
curl -SL https://github.com/docker/compose/releases/download/v2.26.1/docker-compose-linux-x86_64 -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x $DOCKER_CONFIG/docker-compose

echo 'cd /data/airflow && docker compose --profile flower up -d' | sudo tee -a /etc/rc.d/rc.local
chmod +x /etc/rc.d/rc.local

echo "Building and starting airflow" >> /data/airflow/init.log
docker compose up airflow-init
docker compose --profile flower up -d
