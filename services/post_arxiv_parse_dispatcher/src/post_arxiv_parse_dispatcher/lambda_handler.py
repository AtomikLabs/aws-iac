import boto3
import json
import logging
import os

import structlog
from constants import (
    DISPATCH_LAMBDA_NAMES,
    SERVICE_NAME,
    SERVICE_VERSION,
)

structlog.configure(
    [
        structlog.stdlib.filter_by_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.dict_tracebacks,
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()
logger.setLevel(logging.INFO)

lambda_client = boto3.client('lambda')


def lambda_handler(event, context):
    """
    The main entry point for the Lambda function.

    Args:
        event: The event passed to the Lambda function.
        context: The context passed to the Lambda function.

    Returns:
        The response to be returned to the client.
    """
    log_initial_info(event)
    config = get_config()
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']

    event_source = {
        'bucket': bucket,
        'key': key
    }

    function_names = json.loads(config.get(DISPATCH_LAMBDA_NAMES, []))

    logger.info("Dispatching event to consumers",
                method=lambda_handler.__name__,
                event_source=event_source,
                function_names=function_names)

    for function_name in function_names:
        lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='Event',
            Payload=json.dumps(event_source)
        )


def log_initial_info(event: dict) -> None:
    """
    Logs initial info.

    Args:
        event (dict): Event.
    """
    try:
        logger.debug(
            "Log variables",
            method=log_initial_info.__name__,
            log_group=os.environ["AWS_LAMBDA_LOG_GROUP_NAME"],
            log_stream=os.environ["AWS_LAMBDA_LOG_STREAM_NAME"],
        )
        logger.debug("Running on", method=log_initial_info.__name__, platform="AWS")
    except KeyError:
        logger.debug("Running on", method=log_initial_info.__name__, platform="CI/CD or local")
    logger.debug("Event received", method=log_initial_info.__name__, trigger_event=event)


def get_config() -> dict:
    """
    Gets the config from the environment variables.

    Returns:
        dict: The config.
    """
    try:
        config = {
            DISPATCH_LAMBDA_NAMES: os.environ[DISPATCH_LAMBDA_NAMES],
            SERVICE_NAME: os.environ[SERVICE_NAME],
            SERVICE_VERSION: os.environ[SERVICE_VERSION],
        }
        logger.debug("Config", method=get_config.__name__, config=config)
    except KeyError as e:
        logger.error("Missing environment variable", method=get_config.__name__, error=str(e))
        raise e
    logger.debug("Config", method=get_config.__name__, config=config)
    return config
