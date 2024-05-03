#!/bin/bash

LOCK_FILE=/data/.docker_op_complete
if [ -f $LOCK_FILE ]; then
    cd /data/kafka/topics
    source .venv/bin/activate
    pip install -r requirements.txt
    python create_topics.py
    deactivate
fi