#!/bin/bash

cd /data/kafka/topics
source .venv/bin/activate
pip install -r requirements.txt
python create_topics.py
deactivate
