#!/bin/bash

# Initial log for debugging
echo "Starting the volume setup script..." >> /home/ec2-user/init.log

# Attempt to fetch the VOLUME_ID dynamically with a timeout
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
        echo "Waiting for volume ID..." >> /home/ec2-user/init.log
    fi
done

if [[ -z $VOLUME_ID ]]; then
    echo "Failed to fetch VOLUME_ID within the timeout period." >> /home/ec2-user/init.log
    exit 1
fi

echo "VOLUME_ID: $VOLUME_ID" >> /home/ec2-user/init.log

# Ensure the volume is attached
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

# Check and format the filesystem if necessary
FILETYPE=$(sudo file -s $DEVICE_NAME)
echo "File system type: $FILETYPE" >> /home/ec2-user/init.log
if [[ $FILETYPE == *": data"* ]]; then
    echo "Formatting device $DEVICE_NAME" >> /home/ec2-user/init.log
    sudo mkfs -t ext4 $DEVICE_NAME
else
    echo "Device $DEVICE_NAME is already formatted. Checking filesystem." >> /home/ec2-user/init.log
    sudo e2fsck -p -f $DEVICE_NAME
fi

mkdir -p /data/dags /data/logs /data/plugins /data/config
chown -R ec2-user:ec2-user /data/*

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

cd /home/ec2-user

echo -e "AIRFLOW_UID=$(id -u)\nAIRFLOW_GID=0" > /data/.env

cat << 'EOF' > /home/ec2-user/sync_s3.sh
#!/bin/bash
sudo aws s3 sync s3://${infra_bucket_name}/orchestration/airflow/dags /data/dags
sudo aws s3 sync s3://${infra_bucket_name}/orchestration/airflow/plugins /data/plugins
sudo aws s3 sync s3://${infra_bucket_name}/orchestration/airflow/config /data/config
sudo aws s3 cp s3://${infra_bucket_name}/orchestration/airflow/Dockerfile /home/ec2-user/Dockerfile
sudo aws s3 cp s3://${infra_bucket_name}/orchestration/airflow/docker-compose.yml /home/ec2-user/docker-compose.yml
sudo aws s3 cp s3://${infra_bucket_name}/orchestration/airflow/requirements.txt /home/ec2-user/requirements.txt
EOF

chmod +x /home/ec2-user/sync_s3.sh
/home/ec2-user/sync_s3.sh

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

echo 'cd /home/ec2-user && docker compose --profile flower up -d' | sudo tee -a /etc/rc.d/rc.local
chmod +x /etc/rc.d/rc.local

echo "Building and starting airflow" >> /home/ec2-user/init.log
docker compose up airflow-init
docker compose --profile flower up -d
