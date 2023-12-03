import os
import unittest
from unittest.mock import patch, MagicMock
from services.fetch_daily_summaries.src.fetch_daily_summaries \
    import lambda_handler


class TestLambdaHandler(unittest.TestCase):
    @patch('services.fetch_daily_summaries.src.fetch_daily_summaries\
           .process_fetch', return_value=True)
    @patch('services.fetch_daily_summaries.src.fetch_daily_summaries\
           .get_earliest_unfetched_date', return_value='2023-01-01')
    @patch('services.fetch_daily_summaries.src\
           .fetch_daily_summaries.boto3.client')
    @patch('services.fetch_daily_summaries.src\
           .fetch_daily_summaries.requests.get')
    @patch.dict(os.environ, {
        "AWS_DEFAULT_REGION": "us-east-1",
        "RESOURCE_ARN": "mock_resource_arn",
        "SECRET_ARN": "mock_secret_arn",
        "DATABASE_NAME": "mock_database"
    })
    def test_successful_fetch_and_processing(self,
                                             mock_requests,
                                             mock_boto3,
                                             mock_get_earliest_unfetched_date,
                                             mock_process_fetch):
        mock_requests.return_value = MagicMock(status_code=200,
                                               text='<xml>mock response</xml>')
        mock_boto3.return_value = MagicMock()
        event = {
            'base_url': 'http://example.com',
            'bucket_name': 'mybucket',
            'summary_set': 'summary1'}
        context = MagicMock()

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 200)
        self.assertIn('Last successful fetch date', response['body'])
        mock_requests.assert_called_once()
        mock_boto3.assert_called()

    @patch('services.fetch_daily_summaries.src.fetch_daily_summaries\
           .get_earliest_unfetched_date', return_value=None)
    @patch('services.fetch_daily_summaries.src\
           .fetch_daily_summaries.boto3.client')
    @patch.dict(os.environ, {
        "AWS_DEFAULT_REGION": "us-east-1",
        "RESOURCE_ARN": "mock_resource_arn",
        "SECRET_ARN": "mock_secret_arn",
        "DATABASE_NAME": "mock_database"
    })
    def test_no_data_to_fetch(self,
                              mock_boto3,
                              mock_get_earliest_unfetched_date):
        mock_boto3.return_value = MagicMock()
        event = {
            'base_url': 'http://example.com',
            'bucket_name': 'mybucket',
            'summary_set': 'summary1'}
        context = MagicMock()

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 200)
        self.assertIn('No unfetched dates found', response['body'])

    @patch.dict(os.environ, {"AWS_DEFAULT_REGION": "us-east-1"})
    @patch('services.fetch_daily_summaries.src.fetch_daily_summaries\
           .get_earliest_unfetched_date',
           side_effect=Exception("Database error"))
    @patch('services.fetch_daily_summaries.src\
           .fetch_daily_summaries.boto3.client')
    @patch.dict(os.environ, {
        "AWS_DEFAULT_REGION": "us-east-1",
        "RESOURCE_ARN": "mock_resource_arn",
        "SECRET_ARN": "mock_secret_arn",
        "DATABASE_NAME": "mock_database"
    })
    def test_error_handling_database_interaction(
            self,
            mock_boto3,
            mock_get_earliest_unfetched_date):
        mock_client = MagicMock()
        mock_boto3.return_value = mock_client
        mock_client.execute_statement.return_value = {'some_key': 'some_value'}

        event = {
            'base_url': 'http://example.com',
            'bucket_name': 'mybucket',
            'summary_set': 'summary1'}
        context = MagicMock()

        lambda_handler(event, context)
        event = {'base_url': 'http://example.com',
                 'bucket_name': 'mybucket',
                 'summary_set': 'summary1'}
        context = MagicMock()

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 500)
        self.assertIn('Internal server error', response['body'])

    @patch.dict(os.environ, {"AWS_DEFAULT_REGION": "us-east-1"})
    @patch.dict(os.environ, {
        'RESOURCE_ARN': '',
        'SECRET_ARN': '',
        'DATABASE_NAME': ''})
    def test_missing_environment_variables(self):
        event = {
            'base_url': 'http://example.com',
            'bucket_name': 'mybucket',
            'summary_set': 'summary1'}
        context = MagicMock()

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 400)
        self.assertIn('Configuration error', response['body'])
