import json
import os
from datetime import datetime
from logging.config import dictConfig

import boto3
import pytz
import structlog
from avro.schema import Schema, parse
from shared.utils.constants import (
    AWS_GLUE_REGISTRY_NAME,
    AWS_REGION,
    AWS_SECRETS_MANAGER,
    AWS_SECRETS_NEO4J_CREDENTIALS,
    AWS_SECRETS_NEO4J_PASSWORD,
    AWS_SECRETS_NEO4J_USERNAME,
    AWS_SECRETS_STRING,
    DEFAULT_TIMEZONE,
    ENVIRONMENT_NAME,
    LOGGING_CONFIG,
    NEO4J_CONNECTION_RETRIES,
    NEO4J_CONNECTION_RETRIES_DEFAULT,
    NEO4J_PASSWORD,
    NEO4J_URI,
    NEO4J_USERNAME,
    S3_KEY_DATE_FORMAT,
    SCHEMA_DEFINITION,
)

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


def calculate_mb(size: int) -> float:
    """
    Converts bytes to MB.

    Args:
        size (int): Size in bytes.

    Returns:
        float: Size in MB to two decimal places.
    """
    return round(size / (1024 * 1024), 2)


def get_aws_secrets(secret_name: str, region: str, env: str = "") -> dict:
    """
    Get the AWS secrets from the AWS Secrets Manager.

    Args:
        env: The environment to get the secrets for.
        region: The region of the AWS Secrets Manager.
        secret_name: The name of the secret to get.

    Returns:
        The AWS secrets.

    Raises:
        ValueError: If the AWS secrets are not found in the AWS Secrets Manager.
    """
    logger.info("Getting secrets from AWS Secrets Manager", secret_name=secret_name, region=region, env=env)
    secrets_client = boto3.client(AWS_SECRETS_MANAGER, region_name=region)
    secrets_name = env + "/" + secret_name if env else secret_name
    secrets_response = secrets_client.get_secret_value(SecretId=secrets_name)
    secrets_string = secrets_response[AWS_SECRETS_STRING]
    secrets_dict = json.loads(secrets_string)
    if not secrets_dict:
        raise ValueError(f"{secret_name} not found in secrets manager")
    return secrets_dict


def get_schema(schema_name: str) -> Schema:
    glue_client = boto3.client("glue", region_name=os.getenv(AWS_REGION))
    schema_response = glue_client.get_schema_version(
        SchemaId={
            "RegistryName": os.getenv(AWS_GLUE_REGISTRY_NAME),
            "SchemaName": schema_name,
        },
        SchemaVersionNumber={"LatestVersion": True},
    )
    return parse(schema_response.get(SCHEMA_DEFINITION))


def set_neo4j_env_vars(config: dict) -> dict:
    """
    Get the Neo4j environment variables.

    Args:
        config: A config dict to populate.

    Returns:
        config dict with Neo4j environment variables populated.

    """
    neo4j_retries = (
        int(os.getenv(NEO4J_CONNECTION_RETRIES))
        if os.getenv(NEO4J_CONNECTION_RETRIES)
        else int(os.getenv(NEO4J_CONNECTION_RETRIES_DEFAULT))
    )
    config.update(
        [
            (NEO4J_CONNECTION_RETRIES, neo4j_retries),
        ]
    )
    neo4j_secrets_dict = get_aws_secrets(
        AWS_SECRETS_NEO4J_CREDENTIALS, config.get(AWS_REGION), config.get(ENVIRONMENT_NAME)
    )
    config.update(
        [
            (NEO4J_PASSWORD, neo4j_secrets_dict.get(AWS_SECRETS_NEO4J_PASSWORD, "")),
            (NEO4J_USERNAME, neo4j_secrets_dict.get(AWS_SECRETS_NEO4J_USERNAME, "")),
            (NEO4J_URI, os.getenv(NEO4J_URI).replace("'", "")),
        ]
    )
    return config


def get_storage_key(key_prefix: str, key: str, format: str) -> str:
    """
    Gets the storage key for the S3 bucket to store data.

    Args:
        key_prefix (str): The key prefix.
        key (str): The key.
        format (str): The format.

    Returns:
        str: The storage key.
    """
    if not key_prefix or not key or not format:
        logger.error("Key prefix, key, and format are required", method=get_storage_key.__name__)
        raise ValueError("Key prefix, key, and format are required")
    key_date = get_storage_key_date()
    final_key = f"{key_prefix}/{key_date}-{key}.{format}"
    logger.info("Storage key", method=get_storage_key.__name__, key=final_key)
    return final_key


def get_storage_key_date() -> str:
    """
    Get the current date in the format used for S3 keys using the default timezone.

    Returns:
        The current date in the format used for S3 keys.
    """
    return datetime.now().astimezone(pytz.timezone(DEFAULT_TIMEZONE)).strftime(S3_KEY_DATE_FORMAT)


def get_storage_key_datetime() -> datetime:
    """
    Get the date in the format used for S3 keys.

    Returns:
        The date in the format used for S3 keys.

    Raises:
        ValueError: If date_str is not a string.
    """
    return datetime.now().astimezone(pytz.timezone(DEFAULT_TIMEZONE))


def validate_strings(*args):
    for arg in args:
        if not isinstance(arg, str) or not arg.strip():
            return False
    return True
