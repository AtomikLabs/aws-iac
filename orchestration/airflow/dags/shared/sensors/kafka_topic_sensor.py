import json

from airflow.sensors.base import BaseSensorOperator
from airflow.utils.decorators import apply_defaults
from avro.io import validate
from confluent_kafka import Consumer, KafkaError, KafkaException
from dotenv import load_dotenv
from shared.utils.constants import AIRFLOW_DAGS_ENV_PATH, SCHEMA
from shared.utils.utils import get_schema

load_dotenv(dotenv_path=AIRFLOW_DAGS_ENV_PATH)


class KafkaTopicSensor(BaseSensorOperator):

    @apply_defaults
    def __init__(self, topic, schema, task_ids, bootstrap_servers, logger, poke_interval, timeout, *args, **kwargs):
        super(KafkaTopicSensor, self).__init__(*args, **kwargs)
        self.topic = topic
        self.schema = schema
        self.task_ids = task_ids
        self.bootstrap_servers = bootstrap_servers
        self.logger = logger
        self.poke_interval = poke_interval
        self.timeout = timeout
        self.consumer = None

    def poke(self, context):
        if not self.consumer:
            self.consumer = Consumer(
                {
                    "bootstrap.servers": self.bootstrap_servers,
                    "group.id": "airflow_kafka_sensor",
                    "auto.offset.reset": "earliest",
                    "enable.auto.commit": True,
                }
            )
            self.consumer.subscribe([self.topic])

        msg = self.consumer.poll(timeout=1.0)
        if msg is None:
            return False
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                return False
            else:
                raise KafkaException(msg.error())
        else:
            schema = get_schema(self.schema)
            data = msg.value().decode("utf-8")
            data = json.loads(data)
            if not validate(schema, data):
                return False
            context["ti"].xcom_push(key=SCHEMA, value=data)
            return True

    def cleanup(self, context):
        if self.consumer:
            self.consumer.close()
            self.consumer = None
