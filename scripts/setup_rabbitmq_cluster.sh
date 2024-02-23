#!/bin/bash

# Usage check
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <primary_node_private_ip> <secondary_node_private_ip> <path_to_bastion_ssh_private_key>"
    exit 1
fi

PRIMARY_NODE_IP=$1
SECONDARY_NODE_IP=$2
BASTION_KEY_PATH=$3
BASTION_USER="ec2-user"
BASTION_IP="54.147.241.179"

# Function to execute a command on a node via the bastion
execute_via_bastion() {
    local node_ip=$1
    shift
    ssh -i "$BASTION_KEY_PATH" -o ProxyCommand="ssh -W %h:%p -i \"$BASTION_KEY_PATH\" $BASTION_USER@$BASTION_IP" ubuntu@$node_ip "$@"
}

# Copy the Erlang cookie from the primary node to the secondary node with correct permissions
echo "Copying Erlang cookie from primary to secondary node..."
execute_via_bastion $PRIMARY_NODE_IP "sudo cat /var/lib/rabbitmq/.erlang.cookie" | execute_via_bastion $SECONDARY_NODE_IP "sudo tee /var/lib/rabbitmq/.erlang.cookie > /dev/null"

# Set permissions and restart RabbitMQ on the secondary node
execute_via_bastion $SECONDARY_NODE_IP <<'EOF'
sudo chown rabbitmq:rabbitmq /var/lib/rabbitmq/.erlang.cookie
sudo chmod 400 /var/lib/rabbitmq/.erlang.cookie
EOF

# Join the secondary node to the cluster
echo "Joining the secondary node to the cluster..."
execute_via_bastion $SECONDARY_NODE_IP <<EOF
sudo rabbitmqctl stop_app
sudo rabbitmqctl reset
sudo rabbitmqctl join_cluster rabbit@rabbit1
sudo rabbitmqctl start_app
EOF

# Restart RabbitMQ service to ensure changes take effect
execute_via_bastion $SECONDARY_NODE_IP "sudo systemctl restart rabbitmq-server"

# Check the cluster status on the secondary node
echo "Checking the cluster status on the secondary node..."
execute_via_bastion $SECONDARY_NODE_IP "sudo rabbitmqctl cluster_status"

echo "Configuration completed."
