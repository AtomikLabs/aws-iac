from unittest import TestCase
from unittest.mock import MagicMock, patch

from services.fetch_daily_summaries.src.fetch_daily_summaries import persist_to_s3


class TestPersistToS3(TestCase):

    @patch('boto3.resource')
    def test_persist_to_s3(self, mock_boto3_resource):
        bucket_name = 'test_bucket'
        key = 'test_key'
        content = 'test_content'

        mock_bucket = MagicMock()
        mock_boto3_resource.return_value.Bucket.return_value = mock_bucket

        persist_to_s3(bucket_name, key, content)

        mock_boto3_resource.assert_called_once_with('s3')
        mock_boto3_resource.return_value.Bucket.assert_called_once_with(bucket_name)
        mock_bucket.put_object.assert_called_once_with(Key=key, Body=content)

    def test_persist_to_s3_raises_error_when_bucket_name_is_invalid(self):
        with self.assertRaises(ValueError):
            persist_to_s3(None, 'key', 'content')

        with self.assertRaises(ValueError):
            persist_to_s3('', 'key', 'content')

    def test_persist_to_s3_raises_error_when_key_is_invalid(self):
        with self.assertRaises(ValueError):
            persist_to_s3('bucket', None, 'content')

        with self.assertRaises(ValueError):
            persist_to_s3('bucket', '', 'content')

    def test_persist_to_s3_raises_error_when_content_is_invalid(self):
        with self.assertRaises(ValueError):
            persist_to_s3('bucket', 'key', None)

        with self.assertRaises(ValueError):
            persist_to_s3('bucket', 'key', '')