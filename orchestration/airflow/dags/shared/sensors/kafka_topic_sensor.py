from confluent_kafka import Consumer, KafkaError, KafkaException
from airflow.sensors.base import BaseSensorOperator
from airflow.utils.decorators import apply_defaults


class KafkaTopicSensor(BaseSensorOperator):

    @apply_defaults
    def __init__(self, topic, bootstrap_servers, *args, **kwargs):
        super(KafkaTopicSensor, self).__init__(*args, **kwargs)
        self.topic = topic
        self.bootstrap_servers = bootstrap_servers
        self.consumer = None

    def poke(self, context):
        if not self.consumer:
            self.consumer = Consumer({
                "bootstrap.servers": self.bootstrap_servers,
                "group.id": "airflow_kafka_sensor",
                "auto.offset.reset": "earliest",
                "enable.auto.commit": True,
            })
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
            return True

    def cleanup(self, context):
        if self.consumer:
            self.consumer.close()
            self.consumer = None
