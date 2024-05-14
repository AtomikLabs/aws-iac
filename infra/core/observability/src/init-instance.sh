#!/bin/bash
{
yum update -y

yum install -y docker
systemctl start docker
systemctl enable docker

sudo amazon-linux-extras install python3.7 -y

curl -O https://bootstrap.pypa.io/get-pip.py
python3 get-pip.py

sudo curl -L https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m) -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

sudo mkdir /etc/prometheus
sudo mkdir /etc/observability
sudo mkdir -p /var/lib/prometheus/data
sudo chown nobody:nogroup /etc/observability
sudo mkdir -p /var/lib/thanos/data
sudo chown -R 1001:1001 /var/lib/thanos

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

# Enable and start Node Exporter
sudo systemctl daemon-reload
sudo systemctl enable node_exporter.service
sudo systemctl start node_exporter.service

} >> /var/log/user-data.log 2>&1
