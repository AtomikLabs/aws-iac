#!/bin/bash
{
echo "Starting the volume setup script..."

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
    mount -av 2>&1
fi

echo "Volume setup script completed."

echo "Starting RabbitMQ installation"

mkdir /data/rabbitmq

echo "Installing erlang"

# erlang deps
sudo yum groupinstall "Development Tools" -y 
sudo yum install ncurses-devel openssl-devel -y 

# erlang
wget https://github.com/erlang/otp/releases/download/OTP-26.2.2/otp_src_26.2.2.tar.gz
tar -zxvf otp_src_26.2.2.tar.gz
rm -f otp_src_26.2.2.tar.gz
cd otp_src_26.2.2/
./configure
make
sudo make install

echo "Installing RabbitMQ"

if ! grep -q "RABBITMQ_MNESIA_DIR" ~/.bashrc; then
    echo 'export RABBITMQ_MNESIA_DIR=/data/rabbitmq' >> ~/.bashrc
fi

source ~/.bashrc

wget https://github.com/rabbitmq/rabbitmq-server/releases/download/v3.13.0/rabbitmq-server-3.13.0-1.el8.noarch.rpm
sudo rpm --import https://www.rabbitmq.com/rabbitmq-signing-key-public.asc
sudo rpm -Uvh rabbitmq-server-3.13.0-1.el8.noarch.rpm

sudo systemctl enable rabbitmq-server
sudo systemctl start rabbitmq-server

sudo rabbitmq-plugins enable rabbitmq_management

sleep 15

sudo rabbitmqctl add_user ${rabbitmqctl_username} ${rabbitmqctl_password}
sudo rabbitmqctl set_user_tags ${rabbitmqctl_username} administrator
sudo rabbitmqctl set_permissions -p / ${rabbitmqctl_username} ".*" ".*" ".*"

useradd -rs /bin/false node_exporter
cd /tmp
wget https://github.com/prometheus/node_exporter/releases/download/v1.7.0/node_exporter-1.7.0.linux-amd64.tar.gz
tar xvfz node_exporter-1.7.0.linux-amd64.tar.gz
cp node_exporter-1.7.0.linux-amd64/node_exporter /usr/local/bin
chown root:root /usr/local/bin/node_exporter
chmod 755 /usr/local/bin/node_exporter

rm -f node_exporter-1.7.0.linux-amd64.tar.gz

cat <<EOT | sudo tee /etc/systemd/system/node_exporter.service > /dev/null
[Unit]
Description=Prometheus Node Exporter
Wants=network-online.target
After=network-online.target

[Service]
User=node_exporter
Group=node_exporter
Type=simple
ExecStart=/usr/local/bin/node_exporter

[Install]
WantedBy=multi-user.target
EOT

sudo systemctl daemon-reload
sudo systemctl enable node_exporter.service
sudo systemctl start node_exporter.service

echo "Starting the airflow setup script..."

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
echo "Configuring docker"
echo '{
  "data-root": "/data/docker"
}' > /etc/docker/daemon.json

echo "Installing docker"
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

echo "Building and starting airflow"
docker compose -f /data/airflow/docker-compose.yaml up airflow-init
docker compose -f /data/airflow/docker-compose.yaml --profile flower up -d

} >> /var/log/user-data.log 2>&1