import logging
from typing import List

import boto3

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, aurora_cluster_arn, db_credentials_secret_arn, database_name):
        """
        Initialize a Database object.

        Args:
            aurora_cluster_arn (str): The ARN of the Aurora cluster.
            db_credentials_secret_arn (str): The ARN of the secret containing the database credentials.
            database_name (str): The name of the database.

        Returns:
            None

        Raises:
            ValueError: If aurora_cluster_arn is None or an empty string.
            ValueError: If db_credentials_secret_arn is None or an empty string.
            ValueError: If database_name is None or an empty string.
        """
        if not aurora_cluster_arn:
            raise ValueError("aurora_cluster_arn must be a non-empty string")
        if not db_credentials_secret_arn:
            raise ValueError("db_credentials_secret_arn must be a non-empty string")
        if not database_name:
            raise ValueError("database_name must be a non-empty string")
        self.aurora_cluster_arn = aurora_cluster_arn
        self.db_credentials_secret_arn = db_credentials_secret_arn
        self.database_name = database_name

    def execute_sql(self, sql_statement: str, parameters: List[dict]) -> dict:
        """
        Executes the given SQL statement using AWS RDSDataService.

        Args:
            sql_statement (str): SQL statement to execute.
            parameters (List[dict]): List of parameters.

        Returns:
            dict: Response from RDSDataService.

        Raises:
            ValueError: If SQL statement is not provided.
            ValueError: If parameters are not provided.
        """
        if not sql_statement:
            raise ValueError("SQL statement is required")

        if not parameters:
            raise ValueError("Parameters are required")

        if not isinstance(parameters, list):
            raise ValueError("Parameters must be a list")

        client = boto3.client("rds-data")

        try:
            response = client.execute_statement(
                resourceArn=self.aurora_cluster_arn,
                secretArn=self.db_credentials_secret_arn,
                database=self.database_name,
                sql=sql_statement,
                parameters=parameters,
            )
            return response
        except Exception as e:
            logger.error(f"Database query failed: {str(e)}")
            return {}
