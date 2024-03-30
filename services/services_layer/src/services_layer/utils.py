from datetime import datetime

import pytz
from constants import DEFAULT_TIMEZONE, S3_KEY_DATE_FORMAT


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
        if not arg or not isinstance(arg, str):
            return False
    return True
