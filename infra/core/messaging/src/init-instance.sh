#!/bin/bash
{
echo "Starting RabbitMQ installation"

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

wget https://github.com/rabbitmq/rabbitmq-server/releases/download/v3.13.0/rabbitmq-server-3.13.0-1.el8.noarch.rpm
sudo rpm --import https://www.rabbitmq.com/rabbitmq-signing-key-public.asc
sudo rpm -Uvh rabbitmq-server-3.13.0-1.el8.noarch.rpm

sudo systemctl enable rabbitmq-server
sudo systemctl start rabbitmq-server

sudo rabbitmq-plugins enable rabbitmq_management

sleep 15

sudo rabbitmqctl add_user ${local.rabbitmqctl_username} ${local.rabbitmqctl_password}
sudo rabbitmqctl set_user_tags ${local.rabbitmqctl_username} administrator
sudo rabbitmqctl set_permissions -p / ${local.rabbitmqctl_username} ".*" ".*" ".*"

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

} >> /var/log/user-data.log 2>&1
