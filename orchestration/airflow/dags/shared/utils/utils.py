import json
from datetime import datetime

import boto3
import pytz
from dags.shared.utils.constants import AWS_SECRETS_MANAGER, AWS_SECRETS_STRING, DEFAULT_TIMEZONE, S3_KEY_DATE_FORMAT


def get_aws_secrets(secret_name: str, env: str = "") -> dict:
    """
    Get the AWS secrets from the AWS Secrets Manager.

    Args:
        env: The environment to get the secrets for.
        secret_name: The name of the secret to get.

    Returns:
        The AWS secrets.

    Raises:
        ValueError: If the AWS secrets are not found in the AWS Secrets Manager.
    """
    secrets_client = boto3.client(AWS_SECRETS_MANAGER)
    secrets_name = env + "/" + secret_name if env else secret_name
    secrets_response = secrets_client.get_secret_value(SecretId=secrets_name)
    secrets_string = secrets_response[AWS_SECRETS_STRING]
    secrets_dict = json.loads(secrets_string)
    if not secrets_dict:
        raise ValueError(f"{secret_name} not found in secrets manager")
    return secrets_dict


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
