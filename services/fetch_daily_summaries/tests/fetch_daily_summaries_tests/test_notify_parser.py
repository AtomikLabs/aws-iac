from unittest import TestCase
from unittest.mock import patch, MagicMock
import json
from services.fetch_daily_summaries.src.fetch_daily_summaries import notify_parser


class TestNotifyParser(TestCase):
    @patch('boto3.client')
    def test_notify_parser(self, mock_boto3_client):
        mock_lambda = MagicMock()
        mock_boto3_client.return_value = mock_lambda
        lambda_arn = 'arn:aws:lambda:us-west-2:123456789012:function:my-function'
        bucket_name = 'my_bucket'
        key = 'my_key'
        notify_parser(lambda_arn, bucket_name, key)
        mock_boto3_client.assert_called_once_with('lambda')
        mock_lambda.invoke.assert_called_once_with(
            FunctionName=lambda_arn,
            InvocationType='Event',
            Payload=json.dumps({"bucket_name": bucket_name, "key": key})
        )

    @patch('boto3.client')
    def test_notify_parser_no_lambda_arn(self, mock_boto3_client):
        lambda_arn = ''
        bucket_name = 'my_bucket'
        key = 'my_key'
        with self.assertRaises(ValueError):
            notify_parser(lambda_arn, bucket_name, key)

    @patch('boto3.client')
    def test_notify_parser_no_bucket_name(self, mock_boto3_client):
        lambda_arn = 'arn:aws:lambda:us-west-2:123456789012:function:my-function'
        bucket_name = ''
        key = 'my_key'
        with self.assertRaises(ValueError):
            notify_parser(lambda_arn, bucket_name, key)

    @patch('boto3.client')
    def test_notify_parser_no_key(self, mock_boto3_client):
        lambda_arn = 'arn:aws:lambda:us-west-2:123456789012:function:my-function'
        bucket_name = 'my_bucket'
        key = ''
        with self.assertRaises(ValueError):
            notify_parser(lambda_arn, bucket_name, key)
