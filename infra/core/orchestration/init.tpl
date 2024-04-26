#!/bin/bash

VOLUME_ID=$(aws ec2 describe-volumes --filters "Name=tag:Name,Values=${volume_name_tag}" --query "Volumes[*].VolumeId" --output text)
VOLUME_ID=$${VOLUME_ID//-/}
DEVICE_NAME=$(lsblk -d -no NAME,SERIAL | awk -v sn="$VOLUME_ID" '$2 == sn {print "/dev/" $1}')

FILETYPE=$(sudo file -s $DEVICE_NAME)
if [[ $FILETYPE == *": data"* ]]; then
  sudo mkfs -t ext4 $DEVICE_NAME
fi

# Mount the volume if not already mounted
if ! mount | grep -q /data; then
  sudo mount $DEVICE_NAME /data
fi

# Update /etc/fstab to ensure the volume mounts on reboot
grep -q "$DEVICE_NAME" /etc/fstab || echo "$DEVICE_NAME /data ext4 defaults,nofail 0 2" | sudo tee -a /etc/fstab


sudo yum update -y
yum install docker -y
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

DOCKER_CONFIG=/usr/local/lib/docker/cli-plugins
mkdir -p $DOCKER_CONFIG
curl -SL https://github.com/docker/compose/releases/download/v2.26.1/docker-compose-linux-x86_64 -o /usr/local/lib/docker/cli-plugins/docker-compose
sudo chmod +x $DOCKER_CONFIG/docker-compose

echo '{
  "data-root": "/data/docker"
}' > /etc/docker/daemon.json
systemctl restart docker

cd /home/ec2-user

mkdir -p /data/dags /data/logs /data/plugins /data/config
echo -e "AIRFLOW_UID=$(id -u)\nAIRFLOW_GID=0" > /data/.env

cat << 'EOF' > /home/ec2-user/sync_s3.sh
#!/bin/bash
sudo aws s3 sync s3://${infra_bucket_name}/orchestration/airflow/dags /data/dags
sudo aws s3 sync s3://${infra_bucket_name}/orchestration/airflow/plugins /data/plugins
sudo aws s3 sync s3://${infra_bucket_name}/orchestration/airflow/config /data/config
aws s3 sync /data/logs s3://${infra_bucket_name}/orchestration/airflow/logs
sudo aws s3 sync s3://${infra_bucket_name}/orchestration/airflow /home/ec2-user
EOF

chmod +x /home/ec2-user/sync_s3.sh
/home/ec2-user/sync_s3.sh

echo 'cd /home/ec2-user && docker compose --profile flower up -d' | sudo tee -a /etc/rc.d/rc.local
sudo chmod +x /etc/rc.d/rc.local

docker compose up airflow-init
docker compose --profile flower up -d
