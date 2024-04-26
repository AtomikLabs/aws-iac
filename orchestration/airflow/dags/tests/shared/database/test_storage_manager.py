import json

import boto3
import pytest
from moto import mock_aws

from dags.shared.database.storage_manager import StorageManager


@pytest.fixture
def mock_logger(mocker):
    return mocker.Mock()


@pytest.fixture
def storage_manager(mock_logger):
    """Creates a StorageManager instance with mocked dependencies."""
    return StorageManager(bucket_name="test-bucket", logger=mock_logger)


@pytest.mark.parametrize("invalid_bucket_name", [None, "", 123])
def test_storage_manager_init_invalid_bucket_name(invalid_bucket_name, mock_logger):
    """Tests that StorageManager raises a ValueError when initialized with an invalid bucket name."""
    with pytest.raises(ValueError, match="bucket_name must be a non-empty string"):
        StorageManager(bucket_name=invalid_bucket_name, logger=mock_logger)


@mock_aws
def test_load_success(storage_manager, mock_logger):
    """Tests successful loading of content from S3."""
    boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="test-bucket")

    key = "test-key"
    content = "test-content"
    s3 = boto3.resource("s3", region_name="us-east-1")
    s3.Bucket("test-bucket").put_object(Key=key, Body=json.dumps(content))

    loaded_content = storage_manager.load(key=key)

    assert json.loads(loaded_content) == content, "The loaded content should match the content stored in S3."


@mock_aws
def test_load_empty_bucket_name(storage_manager, mock_logger):
    """Tests that load raises a ValueError when the bucket name is empty."""
    with pytest.raises(ValueError, match="Must provide a bucket name"):
        storage_manager.bucket_name = ""
        storage_manager.load(key="test-key")


@mock_aws
def test_load_empty_key(storage_manager, mock_logger):
    """Tests that load raises a ValueError when the key is empty."""
    with pytest.raises(ValueError, match="Must provide a key"):
        storage_manager.load(key="")


@mock_aws
def test_upload_to_s3_success(storage_manager, mock_logger):
    """Tests successful persistence of content to S3."""
    boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="test-bucket")

    key = "test-key"
    content = "test-content"

    storage_manager.upload_to_s3(key=key, content=content)

    s3 = boto3.resource("s3", region_name="us-east-1")
    stored_content = s3.Object("test-bucket", key).get()["Body"].read().decode("utf-8")

    assert stored_content == content, "The content stored in S3 should match the input content."
    mock_logger.debug.assert_called_with(
        "Persisted content to S3", method="upload_to_s3", bucket_name="test-bucket", key=key
    )


@mock_aws
def test_upload_to_s3_empty_key(storage_manager, mock_logger):
    """Tests that persist raises a ValueError when the key is empty."""
    with pytest.raises(ValueError, match="key must be a non-empty string"):
        storage_manager.upload_to_s3(key="", content="test-content")


@mock_aws
def test_upload_to_s3_empty_content(storage_manager, mock_logger):
    """Tests that persist raises a ValueError when the content is empty."""
    with pytest.raises(ValueError, match="content must be a non-empty string"):
        storage_manager.upload_to_s3(key="test-key", content="")


@mock_aws
def test_upload_to_s3_failure(storage_manager, mock_logger, mocker):
    """Tests that persist raises an exception when there is an error persisting the content to S3."""
    key = "test-key"
    content = "test-content"
    mocker.patch("boto3.resource", side_effect=Exception("Test exception"))

    with pytest.raises(Exception, match="Test exception"):
        storage_manager.upload_to_s3(key=key, content=content)

    mock_logger.error.assert_called_with(
        "Failed to persist content to S3",
        method="upload_to_s3",
        bucket_name="test-bucket",
        key=key,
        error="Test exception",
    )
