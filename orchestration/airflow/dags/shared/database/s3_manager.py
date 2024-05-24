from logging.config import dictConfig

import boto3
import structlog
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


class S3Manager:
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

    def delete(self, key: str):
        """
        Delete the content from an AWS S3 bucket with the given key.

        Args:
            key: The key to use when deleting the content from the S3 bucket.

        Raises:
            ValueError: If key is invalid.
            Exception: If there is an error deleting the content from S3.
        """
        if not key or not isinstance(key, str):
            self.logger.error("Invalid key", key=key)
            raise ValueError("key must be a non-empty string")
        self.logger.debug("Deleting content from S3", key=key, bucket_name=self.bucket_name)
        try:
            s3 = boto3.resource("s3", region_name="us-east-1")
            s3.Object(self.bucket_name, key).delete()
            self.logger.debug("Deleted content from S3", key=key, bucket_name=self.bucket_name)
        except Exception as e:
            self.logger.error(
                "Failed to delete content from S3",
                method=self.delete.__name__,
                bucket_name=self.bucket_name,
                key=key,
                error=str(e),
            )
            raise e

    def load(self, key: str):
        """
        Load the content from an AWS S3 bucket with the given key.

        Args:
            key: The key to use when loading the content from the S3 bucket.

        Returns:
            The content stored in the S3 bucket with the given deserialized
            from JSON.
        """
        logger.debug("Loading XML from S3 bucket", method=self.load.__name__, bucket_name=self.bucket_name, key=key)
        if not self.bucket_name:
            logger.error("Must provide a bucket name", method=self.load.__name__, bucket_name=self.bucket_name, key=key)
            raise ValueError("Must provide a bucket name")
        if not key:
            logger.error("Must provide a key", method=self.load.__name__, bucket_name=self.bucket_name, key=key)
            raise ValueError("Must provide a key")
        s3 = boto3.resource("s3")
        obj = s3.Object(self.bucket_name, key)
        body = obj.get()["Body"].read()
        logger.debug("Loaded data from S3 bucket", method=self.load.__name__, bucket_name=self.bucket_name, key=key)
        return body

    def upload_to_s3(self, key: str, content: str, return_presigned_url: bool = False) -> str:
        """
        Persist the content to an AWS S3 bucket with the given key.

        Args:
            key: The key to use when storing the content in the S3 bucket.
            content: The content to store in the S3 bucket.

        Returns:
            A presigned url for the content stored in the S3 bucket if return_presigned_url is True.

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

        self.logger.debug("Persisting content to S3", key=key, bucket_name=self.bucket_name)
        try:
            s3 = boto3.resource("s3")
            s3.Bucket(self.bucket_name).put_object(Key=key, Body=content)
            self.logger.debug(
                "Persisted content to S3", method=self.upload_to_s3.__name__, bucket_name=self.bucket_name, key=key
            )
            if return_presigned_url:
                return s3.meta.client.generate_presigned_url(
                    "get_object", Params={"Bucket": self.bucket_name, "Key": key}, ExpiresIn=3600
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
