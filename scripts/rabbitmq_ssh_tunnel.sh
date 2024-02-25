#!/bin/bash

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <PrivateIP>"
    exit 1
fi

PRIVATE_IP=$1

ssh -L 15672:${PRIVATE_IP}:15672 -N -f -i ~/.ssh/dev-atomiklabs-bastion-keypair.pem ubuntu@54.147.241.179

echo "SSH tunnel established to ${PRIVATE_IP} via 54.147.241.179."
