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

echo "Setting up neo4j"

mkdir -p /data/neo4j/data
mkdir -p /data/neo4j/logs
mkdir -p /data/neo4j/plugins
pushd /data/neo4j/plugins
wget https://github.com/neo4j-contrib/neo4j-apoc-procedures/releases/download/4.1.0.11/apoc-4.1.0.11-all.jar
popd

chown :docker /data/neo4j/data
chown :docker /data/neo4j/logs
chown :docker /data/neo4j/plugins
chmod g+rwx /data/neo4j/data
chmod g+rwx /data/neo4j/logs
chmod g+rwx /data/neo4j/plugins

docker run --restart=always \
--memory=6g \
--cpus=2 \
-p 7474:7474 -p 7687:7687 \
-v /data/neo4j/data:/data \
-v /data/neo4j/logs:/logs \
-v /data/neo4j/plugins:/plugins \
-e NEO4J_AUTH=${neo4j_username}/${neo4j_password} \
-e NEO4J_dbms_security_procedures_unrestricted=apoc.\\\* \
-d \
--name neo4j \
neo4j:4.1

echo "Setting up airflow and kafka"

yum install -y dos2unix

aws s3 cp s3://$ATOMIKLABS_INFRA_BUCKET_NAME/orchestration/$ATOMIKLABS_ENV /data --recursive
chmod +x /data/airflow/host_config/*.sh
chmod +x /data/kafka/host_config/*.sh
chmod 777 -R /data/airflow
chmod 777 -R /data/kafka
dos2unix -f /data/airflow/host_config/*.sh
dos2unix -f /data/kafka/host_config/*.sh

sudo -u ec2-user bash -c "source /etc/environment && /data/airflow/host_config/create.sh"
sudo -u ec2-user bash -c "source /etc/environment && /data/kafka/host_config/create.sh"

touch /data/.docker_volume_initialized

echo "Initialization completed."
