#!/bin/bash

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <PrivateIP> <BastionIP" >&2
    exit 1
fi

PRIVATE_IP=$1
BASTION_IP=$2

ssh -N -f -L localhost:7474:${PRIVATE_IP}:7474 -L localhost:7687:${PRIVATE_IP}:7687 -i ~/.ssh/dev-atomiklabs-bastion-keypair.pem ec2-user@${BASTION_IP}
echo "SSH tunnel established to ${PRIVATE_IP} via ${BASTON_IP}."
