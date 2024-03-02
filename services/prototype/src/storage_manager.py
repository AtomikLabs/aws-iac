import boto3
import structlog

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

# Logging constants
PERSIST = "StorageManager.persist"


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

    def persist(self, key: str, content: str) -> None:
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
            self.logger.info("Persisted content to S3", method=PERSIST, bucket_name=self.bucket_name, key=key)
        except Exception as e:
            self.logger.error(
                "Failed to persist content to S3", method=PERSIST, bucket_name=self.bucket_name, key=key, error=str(e)
            )
            raise e
