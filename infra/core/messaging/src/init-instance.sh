#!/bin/bash
{
echo "Starting RabbitMQ installation"

# Install Erlang
sudo yum install -y wget
wget https://packages.erlang-solutions.com/erlang-solutions-2.0-1.noarch.rpm
sudo rpm -Uvh erlang-solutions-2.0-1.noarch.rpm
sudo yum install -y erlang

# Install RabbitMQ
wget https://github.com/rabbitmq/rabbitmq-server/releases/download/v3.8.9/rabbitmq-server-3.8.9-1.el7.noarch.rpm
sudo rpm --import https://www.rabbitmq.com/rabbitmq-signing-key-public.asc
sudo rpm -Uvh rabbitmq-server-3.8.9-1.el7.noarch.rpm

# Start RabbitMQ service
sudo systemctl enable rabbitmq-server
sudo systemctl start rabbitmq-server

# Enable RabbitMQ management plugin
sudo rabbitmq-plugins enable rabbitmq_management

# Wait for RabbitMQ service to start
sleep 15

# Add RabbitMQ user and set permissions
sudo rabbitmqctl add_user ${local.rabbitmqctl_username} ${local.rabbitmqctl_password}
sudo rabbitmqctl set_user_tags ${local.rabbitmqctl_username} administrator
sudo rabbitmqctl set_permissions -p / ${local.rabbitmqctl_username} ".*" ".*" ".*"

# Install Node Exporter
useradd -rs /bin/false node_exporter
cd /tmp
wget https://github.com/prometheus/node_exporter/releases/download/v1.7.0/node_exporter-1.7.0.linux-amd64.tar.gz
tar xvfz node_exporter-1.7.0.linux-amd64.tar.gz
cp node_exporter-1.7.0.linux-amd64/node_exporter /usr/local/bin
chown root:root /usr/local/bin/node_exporter
chmod 755 /usr/local/bin/node_exporter

# Clean up the downloaded tar.gz file
rm -f node_exporter-1.7.0.linux-amd64.tar.gz

# Create a systemd service file for Node Exporter
cat <<EOT > /etc/systemd/system/node_exporter.service
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

# Reload system daemons and start Node Exporter
systemctl daemon-reload
systemctl enable --now node_exporter

} >> /var/log/user-data.log 2>&1
