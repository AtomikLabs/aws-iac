#!/bin/bash

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <pem_key> <user_ip>"
    exit 1
fi

PEM_KEY=$1
USER_IP=$2

eval $(ssh-agent -s)
ssh-add $PEM_KEY
echo "Key added to ssh-agent."
ssh -A ec2-user@$USER_IP
