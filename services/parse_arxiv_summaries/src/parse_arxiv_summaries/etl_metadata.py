import json
import uuid
from datetime import datetime

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

logger = structlog.get_logger()

# Logging Constants
ETL_METADATA = "ETLMetadata"
ETL_METADATA_PREFIX = "metadata/etl/"
GET_SCHEMA = "ETLMetadata.get_schema"
VALIDATE = "ETLMetadata.validate"


class ETLMetadata:
    """
    ETLMetadata is a class that represents the metadata of a ETL job.

    The schema of the metadata must match the definition in the AWS Glue Data Catalog.
    """
    # TODO: Refactor for ETL specific metadata
    DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f%z"
    S3_KEY_DATE_FORMAT = "%Y-%m-%dT%H-%M-%S"

    app_name: str
    date_time: str
    data_source: str
    database_name: str
    environment: str
    error_message: str
    function_name: str
    function_version: str
    etl_job_uuid: uuid.UUID
    metadata_bucket: str
    metadata_key: str
    original_data_format: str
    raw_data_bucket: str
    raw_data_key: str
    size_of_data_downloaded: float
    status: str
    stored_data_format: str
    table_name: str
    triggered_functions: list
    uri: str

    def __init__(self):
        self.etl_job_uuid = uuid.uuid4()
        self.app_name = ""
        self.date_time = datetime.now().strftime(self.DATETIME_FORMAT)
        self.data_source = ""
        self.database_name = ""
        self.environment = ""
        self.error_message = ""
        self.function_name = ""
        self.function_version = ""
        self.location_raw_data_saved = ""
        self.metadata_bucket = ""
        self.metadata_key = ""
        self.original_data_format = ""
        self.raw_data_bucket = ""
        self.raw_data_key = ""
        self.size_of_data_downloaded = 0.0
        self.status = ""
        self.stored_data_format = ""
        self.table_name = ""
        self.triggered_functions = []
        self.uri = ""

    @property
    def app_name(self) -> str:
        return self._app_name

    @app_name.setter
    def app_name(self, app_name: str):
        if not isinstance(app_name, str):
            raise ValueError("app_name must be a string")
        self._app_name = app_name

    @property
    def date_time(self) -> str:
        return self._date_time

    @date_time.setter
    def date_time(self, date_time):
        if not isinstance(date_time, datetime) and not isinstance(date_time, str):
            raise ValueError("date_time must be a datetime or a string")
        if isinstance(date_time, datetime):
            self._date_time = date_time.strftime(self.DATETIME_FORMAT)
        else:
            self._date_time = date_time

    @property
    def data_source(self) -> str:
        return self._data_source

    @data_source.setter
    def data_source(self, data_source: str):
        if not isinstance(data_source, str):
            raise ValueError("data_source must be a string")
        self._data_source = data_source

    @property
    def database_name(self) -> str:
        return self._database_name

    @database_name.setter
    def database_name(self, database_name: str):
        if not isinstance(database_name, str):
            raise ValueError("database_name must be a string")
        self._database_name = database_name

    @property
    def environment(self) -> str:
        return self._environment

    @environment.setter
    def environment(self, environment: str):
        if not isinstance(environment, str):
            raise ValueError("environment must be a string")
        self._environment = environment

    @property
    def error_message(self) -> str:
        return self._error_message

    @error_message.setter
    def error_message(self, error_message: str):
        if not isinstance(error_message, str):
            raise ValueError("error_message must be a string")
        self._error_message = error_message

    @property
    def function_name(self) -> str:
        return self._function_name

    @function_name.setter
    def function_name(self, function_name: str):
        if not isinstance(function_name, str):
            raise ValueError("function_name must be a string")
        self._function_name = function_name

    @property
    def function_version(self) -> str:
        return self._function_version

    @function_version.setter
    def function_version(self, function_version: str):
        if not isinstance(function_version, str):
            raise ValueError("function_version must be a string")
        self._function_version = function_version

    @property
    def etl_job_uuid(self) -> uuid.UUID:
        return self._etl_job_uuid

    @etl_job_uuid.setter
    def etl_job_uuid(self, etl_job_uuid: uuid.UUID):
        if not isinstance(etl_job_uuid, uuid.UUID):
            raise ValueError("etl_job_uuid must be a uuid")
        self._etl_job_uuid = etl_job_uuid

    @property
    def location_raw_data_saved(self) -> str:
        return self._location_raw_data_saved

    @location_raw_data_saved.setter
    def location_raw_data_saved(self, location_raw_data_saved: str):
        if not isinstance(location_raw_data_saved, str):
            raise ValueError("location_raw_data_saved must be a string")
        self._location_raw_data_saved = location_raw_data_saved

    @property
    def metadata_bucket(self) -> str:
        return self._metadata_bucket

    @metadata_bucket.setter
    def metadata_bucket(self, metadata_bucket: str):
        if not isinstance(metadata_bucket, str):
            raise ValueError("metadata_bucket must be a string")
        self._metadata_bucket = metadata_bucket

    @property
    def metadata_key(self) -> str:
        return self._metadata_key

    @metadata_key.setter
    def metadata_key(self, metadata_key: str):
        if not isinstance(metadata_key, str):
            raise ValueError("metadata_key must be a string")
        self._metadata_key = metadata_key

    @property
    def original_data_format(self) -> str:
        return self._original_data_format

    @original_data_format.setter
    def original_data_format(self, original_data_format: str):
        if not isinstance(original_data_format, str):
            raise ValueError("original_data_format must be a string")
        self._original_data_format = original_data_format

    @property
    def raw_data_bucket(self) -> str:
        return self._raw_data_bucket

    @raw_data_bucket.setter
    def raw_data_bucket(self, raw_data_bucket: str):
        if not isinstance(raw_data_bucket, str):
            raise ValueError("raw_data_bucket must be a string")
        self._raw_data_bucket = raw_data_bucket

    @property
    def raw_data_key(self) -> str:
        return self._raw_data_key

    @raw_data_key.setter
    def raw_data_key(self, raw_data_key: str):
        if not isinstance(raw_data_key, str):
            raise ValueError("raw_data_key must be a string")
        self._raw_data_key = raw_data_key

    @property
    def size_of_data_downloaded(self) -> float:
        return self._size_of_data_downloaded

    @size_of_data_downloaded.setter
    def size_of_data_downloaded(self, size_of_data_downloaded: float):
        if not isinstance(size_of_data_downloaded, float):
            raise ValueError("size_of_data_downloaded must be a float")
        self._size_of_data_downloaded = size_of_data_downloaded

    @property
    def status(self) -> str:
        return self._status

    @status.setter
    def status(self, status: str):
        if not isinstance(status, str):
            raise ValueError("status must be a string")
        self._status = status

    @property
    def stored_data_format(self) -> str:
        return self._stored_data_format

    @stored_data_format.setter
    def stored_data_format(self, stored_data_format: str):
        if not isinstance(stored_data_format, str):
            raise ValueError("stored_data_format must be a string")
        self._stored_data_format = stored_data_format

    @property
    def table_name(self) -> str:
        return self._table_name

    @table_name.setter
    def table_name(self, table_name: str):
        if not isinstance(table_name, str):
            raise ValueError("table_name must be a string")
        self._table_name = table_name

    @property
    def triggered_functions(self) -> list:
        return self._triggered_functions

    @triggered_functions.setter
    def triggered_functions(self, triggered_functions: list):
        if not isinstance(triggered_functions, list):
            raise ValueError("triggered_functions must be a list")
        self._triggered_functions = triggered_functions

    @property
    def uri(self) -> str:
        return self._uri

    @uri.setter
    def uri(self, uri: str):
        if not isinstance(uri, str):
            raise ValueError("uri must be a string")
        self._uri = uri

    def validate(self) -> bool:
        """
        Validate the metadata against the schema of the table.

        Returns:
            bool: True if the metadata is valid, False otherwise.
        """
        logger.info("Validating ETL metadata", method=VALIDATE)
        if not self.database_name or not self.table_name:
            logger.error("Database name and table name must be set", method=VALIDATE)
            raise ValueError("Database name and table name must be set")
        table_schema = self.get_schema(self.database_name, self.table_name)
        for column in table_schema["StorageDescriptor"]["Columns"]:
            if not hasattr(self, column["Name"]):
                logger.error(f"Metadata is missing attribute {column['Name']}")
                return False
        return True

    def get_schema(self, database_name: str, table_name: str) -> dict:
        """
        Get the schema of the table from the AWS Glue Data Catalog.

        Args:
            database_name (str): The name of the database.
            table_name (str): The name of the table.

        Returns:
            dict: The schema of the table.
        """
        logger.info(
            "Getting ETL metadata schema",
            database_name=database_name,
            table_name=table_name,
            method=GET_SCHEMA,
        )
        client = boto3.client("glue")
        response = client.get_table(DatabaseName=database_name, Name=table_name)
        logger.debug(
            "Got ETL metadata schema",
            database_name=database_name,
            table_name=table_name,
            method=GET_SCHEMA,
            response=response,
        )
        return response["Table"]

    def write(self) -> None:
        """
        Write the metadata to the metadata bucket.
        """
        logger.info("Writing ETL metadata", method=f"{ETL_METADATA}.write")
        try:
            client = boto3.client("s3")
            metadata_dict = self.to_dict()
            client.put_object(
                Body=json.dumps(metadata_dict).encode("utf-8"),
                Bucket=self.metadata_bucket,
                Key=f"{ETL_METADATA_PREFIX}{self.date_time}-{self.etl_job_uuid}.json",
            )
            logger.info("Wrote ETL metadata", method=f"{ETL_METADATA}.write")
        except Exception as e:
            logger.error(
                "Failed to write ETL metadata",
                method=f"{ETL_METADATA}.write",
                error_message=str(e),
            )
            raise e

    def to_dict(self) -> dict:
        """
        Convert the metadata to a dictionary.

        Returns:
            dict: The metadata as a dictionary.
        """
        return {
            "app_name": self.app_name,
            "date_time": self.date_time,
            "data_source": self.data_source,
            "database_name": self.database_name,
            "environment": self.environment,
            "error_message": self.error_message,
            "function_name": self.function_name,
            "function_version": self.function_version,
            "etl_job_uuid": str(self.etl_job_uuid),
            "metadata_bucket": self.metadata_bucket,
            "metadata_key": self.metadata_key,
            "original_data_format": self.original_data_format,
            "raw_data_bucket": self.raw_data_bucket,
            "raw_data_key": self.raw_data_key,
            "size_of_data_downloaded": self.size_of_data_downloaded,
            "status": self.status,
            "stored_data_format": self.stored_data_format,
            "table_name": self.table_name,
            "triggered_functions": self.triggered_functions,
            "uri": self.uri,
        }

    def from_dict(self, data: dict) -> None:
        """
        Load the metadata from a dictionary.

        Args:
            data (dict): The metadata as a dictionary.
        """
        self.app_name = data["app_name"]
        self.date_time = data["date_time"]
        self.data_source = data["data_source"]
        self.database_name = data["database_name"]
        self.environment = data["environment"]
        self.error_message = data["error_message"]
        self.function_name = data["function_name"]
        self.function_version = data["function_version"]
        self.etl_job_uuid = uuid.UUID(data["etl_job_uuid"])
        self.metadata_bucket = data["metadata_bucket"]
        self.metadata_key = data["metadata_key"]
        self.original_data_format = data["original_data_format"]
        self.raw_data_bucket = data["raw_data_bucket"]
        self.raw_data_key = data["raw_data_key"]
        self.size_of_data_downloaded = data["size_of_data_downloaded"]
        self.status = data["status"]
        self.stored_data_format = data["stored_data_format"]
        self.table_name = data["table_name"]
        self.triggered_functions = data["triggered_functions"]
        self.uri = data["uri"]
