#!/bin/bash

sudo yum update -y
yum install docker -y
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

DOCKER_CONFIG=$${DOCKER_CONFIG:/usr/local/lib/docker/cli-plugins}
mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL https://github.com/docker/compose/releases/download/v2.26.1/docker-compose-linux-x86_64 -o /usr/local/lib/docker/cli-plugins/docker-compose
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

cd /home/ec2-user

curl -LfO 'https://airflow.apache.org/docs/apache-airflow/2.9.0/docker-compose.yaml'

mkdir -p ./dags ./logs ./plugins ./config
echo -e "AIRFLOW_UID=$(id -u)" > .env

# Add startup script to rc.local
echo 'cd /home/ec2-user && docker compose --profile flower up -d' | sudo tee -a /etc/rc.d/rc.local
sudo chmod +x /etc/rc.d/rc.local

docker compose up airflow-init
docker compose --profile flower up -d

cat << 'EOF' > /home/ec2-user/sync_s3.sh
#!/bin/bash
aws s3 sync s3://${bucket_name}/dags /home/ec2-user/dags
aws s3 sync s3://${bucket_name}/plugins /home/ec2-user/plugins
aws s3 sync s3://${bucket_name}/config /home/ec2-user/config
aws s3 sync s3://${bucket_name}/config /home/ec2-user/logs
EOF

chmod +x /home/ec2-user/sync_s3.sh

touch /home/ec2-user/logs/test.log

(crontab -l 2>/dev/null; echo "0 * * * * /home/ec2-user/sync_s3.sh") | crontab -