import asyncio
from logging.config import dictConfig

import structlog
from aiokafka import AIOKafkaConsumer
from airflow.sensors.base import BaseSensorOperator
from airflow.utils.decorators import apply_defaults
from shared.utils.constants import LOGGING_CONFIG

dictConfig(LOGGING_CONFIG)

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


class KafkaTopicSensor(BaseSensorOperator):
    @apply_defaults
    def __init__(self, topic, bootstrap_servers, consumer_timeout_ms=3600, poke_interval=60, *args, **kwargs):
        super(KafkaTopicSensor, self).__init__(*args, **kwargs)
        self.topic = topic
        self.bootstrap_servers = bootstrap_servers
        self.consumer_timeout_ms = consumer_timeout_ms
        self.poke_interval = poke_interval

    def poke(self, context):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.async_poke(context))

    async def async_poke(self, context):
        consumer = AIOKafkaConsumer(
            self.topic, bootstrap_servers=self.bootstrap_servers, consumer_timeout_ms=self.consumer_timeout_ms
        )
        await consumer.start()
        try:
            async for msg in consumer:
                logger.info(f"Received message: {msg.value} on topic: {msg.topic}")
                return True
            await asyncio.sleep(self.poke_interval)
        except asyncio.TimeoutError:
            logger.info("Timeout, no message received.")
            return False
        finally:
            await consumer.stop()

        return False
