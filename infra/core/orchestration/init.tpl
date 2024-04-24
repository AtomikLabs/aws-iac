#!/bin/bash

sudo yum update -y
yum install docker -y
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

DOCKER_CONFIG=/usr/local/lib/docker/cli-plugins
mkdir -p $DOCKER_CONFIG
curl -SL https://github.com/docker/compose/releases/download/v2.26.1/docker-compose-linux-x86_64 -o /usr/local/lib/docker/cli-plugins/docker-compose
sudo chmod +x $DOCKER_CONFIG/docker-compose

cd /home/ec2-user

aws s3 cp s3://${infra_bucket_name}/orchestration/airflow/docker-compose.yml /home/ec2-user/docker-compose.yml

mkdir -p ./dags ./logs ./plugins ./config
echo -e "AIRFLOW_UID=$(id -u)" > .env

echo 'cd /home/ec2-user && docker compose --profile flower up -d' | sudo tee -a /etc/rc.d/rc.local
sudo chmod +x /etc/rc.d/rc.local

export AIRFLOW__CORE__LOAD_EXAMPLES=False
docker compose up airflow-init
docker compose --profile flower up -d

cat << 'EOF' > /home/ec2-user/sync_s3.sh
#!/bin/bash
aws s3 sync s3://${bucket_name}/orchestration/dags /home/ec2-user/dags
aws s3 sync /home/ec2-user/dags s3://${bucket_name}/orchestration/dags
aws s3 sync s3://${bucket_name}/orchestration/plugins /home/ec2-user/plugins
aws s3 sync /home/ec2-user/plugins s3://${bucket_name}/orchestration/plugins
aws s3 sync s3://${bucket_name}/orchestration/config /home/ec2-user/config
aws s3 sync /home/ec2-user/config s3://${bucket_name}/orchestration/config
aws s3 sync s3://${bucket_name}/orchestration/config /home/ec2-user/logs
aws s3 sync /home/ec2-user/logs s3://${bucket_name}/orchestration/logs
EOF

chmod +x /home/ec2-user/sync_s3.sh

touch /home/ec2-user/logs/test.log

/home/ec2-user/sync_s3.sh