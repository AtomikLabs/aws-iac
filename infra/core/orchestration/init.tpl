#!/bin/bash

file -s /dev/sdh | grep -q ext4 || mkfs -t ext4 /dev/sdh

if ! mount | grep -q /data; then
  mount /dev/sdh /data
fi
echo '/dev/sdh /data ext4 defaults,nofail 0 2' >> /etc/fstab

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

aws s3 cp s3://${infra_bucket_name}/orchestration/airflow/docker-compose.yaml /home/ec2-user/docker-compose.yaml

mkdir -p /data/dags /data/logs /data/plugins /data/config
echo -e "AIRFLOW_UID=$(id -u)\nAIRFLOW_GID=0" > /data/.env

echo 'cd /home/ec2-user && docker compose --profile flower up -d' | sudo tee -a /etc/rc.d/rc.local
sudo chmod +x /etc/rc.d/rc.local

export AIRFLOW__CORE__LOAD_EXAMPLES=False
docker compose up airflow-init
docker compose --profile flower up -d

cat << 'EOF' > /home/ec2-user/sync_s3.sh
#!/bin/bash
sudo aws s3 sync s3://${infra_bucket_name}/orchestration/airflow/dags /data/dags
aws s3 sync /data/dags s3://${infra_bucket_name}/orchestration/airflow/dags
sudo aws s3 sync s3://${infra_bucket_name}/orchestration/airflow/plugins /data/plugins
aws s3 sync /data/plugins s3://${infra_bucket_name}/orchestration/airflow/plugins
sudo aws s3 sync s3://${infra_bucket_name}/orchestration/airflow/config /data/config
aws s3 sync /data/config s3://${infra_bucket_name}/orchestration/airflow/config
sudo aws s3 sync s3://${infra_bucket_name}/orchestration/airflow/logs /data/logs
aws s3 sync /data/logs s3://${infra_bucket_name}/orchestration/airflow/logs
EOF

chmod +x /home/ec2-user/sync_s3.sh
chmod +x /etc/rc.d/rc.local
/home/ec2-user/sync_s3.sh
