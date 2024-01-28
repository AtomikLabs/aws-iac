from unittest import TestCase

from services.fetch_daily_summaries.src.database import Database


class TestInit(TestCase):
    aurora_cluster_arn = "arn:aws:rds:us-west-2:123456789012:cluster:my-aurora-cluster"
    db_credentials_secret_arn = "arn:aws:secretsmanager:us-west-2:123456789012:secret:my-db-credentials"
    database_name = "mydatabase"

    def test_init(self):
        database = Database(self.aurora_cluster_arn, self.db_credentials_secret_arn, self.database_name)

        self.assertEqual(database.aurora_cluster_arn, self.aurora_cluster_arn)
        self.assertEqual(database.db_credentials_secret_arn, self.db_credentials_secret_arn)
        self.assertEqual(database.database_name, self.database_name)

    def test_init_with_invalid_inputs(self):
        invalid_inputs = [
            (None, self.db_credentials_secret_arn, self.database_name),
            ("", self.db_credentials_secret_arn, self.database_name),
            (self.aurora_cluster_arn, None, self.database_name),
            (self.aurora_cluster_arn, "", self.database_name),
            (self.aurora_cluster_arn, self.db_credentials_secret_arn, None),
            (self.aurora_cluster_arn, self.db_credentials_secret_arn, ""),
        ]

        for inputs in invalid_inputs:
            with self.assertRaises(ValueError, msg=f"Expected ValueError for inputs {inputs}"):
                Database(*inputs)
