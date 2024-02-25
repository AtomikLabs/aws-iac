#!/bin/bash
{
# Update the instance
yum update -y

# Install Docker
yum install -y docker
systemctl start docker
systemctl enable docker

# Python 3.7
sudo amazon-linux-extras install python3.7 -y

curl -O https://bootstrap.pypa.io/get-pip.py
python3 get-pip.py

# Install Docker Compose
sudo curl -L https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m) -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Create Observability dirs
mkdir /etc/prometheus
mkdir /etc/observability
mkdir -p /var/lib/prometheus/data
mkdir -p /var/lib/thanos/data

# Install Node Exporter
useradd -rs /bin/false node_exporter
cd /tmp
wget https://github.com/prometheus/node_exporter/releases/download/v1.7.0/node_exporter-1.7.0.linux-amd64.tar.gz
tar xvfz node_exporter-1.7.0.linux-amd64.tar.gz
cp node_exporter-1.7.0.linux-amd64/node_exporter /usr/local/bin
chown root:root /usr/local/bin/node_exporter
chmod 755 /usr/local/bin/node_exporter
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

# Enable and start Node Exporter
systemctl daemon-reload
systemctl enable --now node_exporter

} >> /var/log/user-data.log 2>&1
