from datetime import datetime

import boto3
import pytz
import structlog
from constants import DEFAULT_TIMEZONE, S3_KEY_DATE_FORMAT

structlog.configure(
    [
        structlog.stdlib.filter_by_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.dict_tracebacks,
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()


class StorageManager:
    """
    A class to manage the storage of data in an AWS S3 bucket.
    """

    def __init__(self, bucket_name: str, logger=None):
        if not logger:
            self.logger = structlog.get_logger()
        else:
            self.logger = logger
        if not bucket_name or not isinstance(bucket_name, str):
            logger.error("Invalid bucket_name", bucket_name=bucket_name)
            raise ValueError("bucket_name must be a non-empty string")
        self.bucket_name = bucket_name

    @staticmethod
    def get_storage_key_date() -> str:
        """
        Get the current date in the format used for S3 keys using the default timezone.

        Returns:
            The current date in the format used for S3 keys.
        """
        storage_date = datetime.now().astimezone(pytz.timezone(DEFAULT_TIMEZONE))
        return storage_date.strftime(S3_KEY_DATE_FORMAT)

    def get_storage_key_datetime(self, date: str = "") -> datetime:
        """
        Get the date in the format used for S3 keys.

        Args:
            date: The date to format.

        Returns:
            The date in the format used for S3 keys.
        """
        if not date:
            return datetime.now().astimezone(pytz.timezone(DEFAULT_TIMEZONE))
        return datetime.strptime(date, S3_KEY_DATE_FORMAT).astimezone(pytz.timezone(DEFAULT_TIMEZONE))

    def load(self, key: str):
        """
        Load the content from an AWS S3 bucket with the given key.

        Args:
            key: The key to use when loading the content from the S3 bucket.

        Returns:
            The content stored in the S3 bucket with the given deserialized
            from JSON.
        """
        logger.info("Loading XML from S3 bucket", method=self.load.__name__, bucket_name=self.bucket_name, key=key)
        if not self.bucket_name:
            logger.error("Must provide a bucket name", method=self.load.__name__, bucket_name=self.bucket_name, key=key)
            raise ValueError("Must provide a bucket name")
        if not key:
            logger.error("Must provide a key", method=self.load.__name__, bucket_name=self.bucket_name, key=key)
            raise ValueError("Must provide a key")
        s3 = boto3.resource("s3")
        obj = s3.Object(self.bucket_name, key)
        body = obj.get()["Body"].read()
        logger.info("Loaded data from S3 bucket", method=self.load.__name__, bucket_name=self.bucket_name, key=key)
        return body

    def upload_to_s3(self, key: str, content: str) -> None:
        """
        Persist the content to an AWS S3 bucket with the given key.

        Args:
            key: The key to use when storing the content in the S3 bucket.
            content: The content to store in the S3 bucket.

        Raises:
            ValueError: If key or content are invalid.
            Exception: If there is an error persisting the content to S3.
        """
        if not key or not isinstance(key, str):
            self.logger.error("Invalid key", key=key)
            raise ValueError("key must be a non-empty string")
        if not content or not isinstance(content, str):
            self.logger.error("Invalid content", content=content)
            raise ValueError("content must be a non-empty string")

        self.logger.info("Persisting content to S3", key=key, bucket_name=self.bucket_name)
        try:
            s3 = boto3.resource("s3")
            s3.Bucket(self.bucket_name).put_object(Key=key, Body=content)
            self.logger.info(
                "Persisted content to S3", method=self.upload_to_s3.__name__, bucket_name=self.bucket_name, key=key
            )
        except Exception as e:
            self.logger.error(
                "Failed to persist content to S3",
                method=self.upload_to_s3.__name__,
                bucket_name=self.bucket_name,
                key=key,
                error=str(e),
            )
            raise e
