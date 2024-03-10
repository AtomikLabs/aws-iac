import boto3
import pytest
from moto import mock_aws

from services.parse_arxiv_summaries.src.parse_arxiv_summaries.storage_manager import StorageManager


@pytest.fixture
def mock_logger(mocker):
    return mocker.Mock()


@pytest.fixture
def storage_manager(mock_logger):
    """Creates a StorageManager instance with mocked dependencies."""
    return StorageManager(bucket_name="test-bucket", logger=mock_logger)


@mock_aws
def test_persist_success(storage_manager, mock_logger):
    """Tests successful persistence of content to S3."""
    boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="test-bucket")

    key = "test-key"
    content = "test-content"

    storage_manager.persist(key=key, content=content)

    s3 = boto3.resource("s3", region_name="us-east-1")
    stored_content = s3.Object("test-bucket", key).get()["Body"].read().decode("utf-8")

    assert stored_content == content, "The content stored in S3 should match the input content."
    mock_logger.info.assert_called_with(
        "Persisted content to S3", method="StorageManager.persist", bucket_name="test-bucket", key=key
    )
