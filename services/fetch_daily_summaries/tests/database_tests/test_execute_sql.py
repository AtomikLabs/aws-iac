from unittest import TestCase
from unittest.mock import patch

from services.fetch_daily_summaries.src.database import Database


class TestExecuteSql(TestCase):
    aurora_cluster_arn = "arn:aws:rds:us-west-2:123456789012:cluster:my-aurora-cluster"
    db_credentials_secret_arn = "arn:aws:secretsmanager:us-west-2:123456789012:secret:my-db-credentials"
    database_name = "mydatabase"
    database: Database = None

    def setUp(self):
        self.database = Database(
            self.aurora_cluster_arn,
            self.db_credentials_secret_arn,
            self.database_name,
        )

    @patch("boto3.client")
    def test_execute_sql(self, mock_client):
        mock_client.return_value.execute_statement.return_value = {"records": []}

        sql_statement = "SELECT * FROM table"
        parameters = [{"name": "param", "value": {"stringValue": "value"}}]

        self.database.execute_sql(sql_statement, parameters)

        mock_client.assert_called_once_with("rds-data")
        mock_client.return_value.execute_statement.assert_called_once_with(
            resourceArn=self.aurora_cluster_arn,
            secretArn=self.db_credentials_secret_arn,
            database=self.database_name,
            sql=sql_statement,
            parameters=parameters,
        )

    def test_execute_sql_with_invalid_inputs(self):
        invalid_inputs = [
            (None, list({"name": "param", "value": {"stringValue": "value"}})),
            ("", list({"name": "param", "value": {"stringValue": "value"}})),
            ("SELECT * FROM table", None),
            ("SELECT * FROM table", list({})),
            ("SELECT * FROM table", "invalid"),
            ("SELECT * FROM table", 123),
        ]

        for inputs in invalid_inputs:
            with self.assertRaises(ValueError or TypeError, msg=f"Expected ValueError for inputs {inputs}"):
                self.database.execute_sql(*inputs)
