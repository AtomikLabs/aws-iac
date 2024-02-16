from datetime import datetime, timezone
import json
import uuid

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
DATA_INGESTION_METADATA = "DataIngestionMetadata"
DATA_INGESTION_METADATA_PREFIX = "metadata/data-ingestion/"
GET_SCHEMA = "DataIngestionMetadata.get_schema"
VALIDATE = "DataIngestionMetadata.validate"


class DataIngestionMetadata:
    """
    DataIngestionMetadata is a class that represents the metadata of a data ingestion job.

    The schema of the metadata must match the definition in the AWS Glue Data Catalog.
    """
    DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f%z"
    S3_KEY_DATE_FORMAT = "%Y-%m-%dT%H-%M-%S"

    uuid = uuid.uuid4()

    def __init__(self, **kwargs):
        self.app_name = kwargs.get('app_name')
        self.data_source = kwargs.get('data_source')
        self.date_time = kwargs.get('date_time') or datetime.now(timezone.utc).strftime(self.DATETIME_FORMAT)
        self.database_name = kwargs.get('database_name')
        self.environment = kwargs.get('environment')
        self.error_message = kwargs.get('error_message')
        self.function_name = kwargs.get('function_name')
        self.ingestion_job_uuid = kwargs.get('ingestion_job_uuid')
        self.metadata_bucket = kwargs.get('metadata_bucket')
        self.original_data_format = kwargs.get('original_data_format')
        self.raw_data_bucket = kwargs.get('raw_data_bucket')
        self.raw_data_key = kwargs.get('raw_data_key')
        self.size_of_data_downloaded = kwargs.get('size_of_data_downloaded')
        self.status = kwargs.get('status')
        self.stored_data_format = kwargs.get('stored_data_format')
        self.table_name = kwargs.get('table_name')
        self.triggered_functions = kwargs.get('triggered_functions')
        self.uri = kwargs.get('uri')

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
    def date_time(self, date_time: datetime):
        if not isinstance(date_time, datetime) and not isinstance(date_time, str):
            raise ValueError("date_time must be a datetime or a string")
        if isinstance(date_time, datetime):
            self.date_time.strftime(self.DATETIME_FORMAT)
        else:
            self.date_time = date_time

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
    def ingestion_job_uuid(self) -> str:
        return self._ingestion_job_uuid

    @ingestion_job_uuid.setter
    def ingestion_job_uuid(self, ingestion_job_uuid: str):
        if not isinstance(ingestion_job_uuid, str):
            raise ValueError("ingestion_job_uuid must be a string")
        self._ingestion_job_uuid = ingestion_job_uuid

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
    def size_of_data_downloaded(self) -> str:
        return self._size_of_data_downloaded

    @size_of_data_downloaded.setter
    def size_of_data_downloaded(self, size_of_data_downloaded: str):
        if not isinstance(size_of_data_downloaded, str):
            raise ValueError("size_of_data_downloaded must be a string")
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

    def get_schema(self, database_name: str, table_name: str) -> dict:
        """
        Get the schema of the table from the AWS Glue Data Catalog.

        Args:
            database_name (str): The name of the database.
            table_name (str): The name of the table.

        Returns:
            dict: The schema of the table.
        """
        logger.info("Getting data ingestion metadata schema", database_name=database_name, table_name=table_name, method=GET_SCHEMA)
        client = boto3.client("glue")
        response = client.get_table(DatabaseName=database_name, Name=table_name)
        logger.debug("Got data ingestion metadata schema", database_name=database_name, table_name=table_name, method=GET_SCHEMA, response=response)
        return response["Table"]

    def validate(self, table_schema: dict) -> bool:
        """
        Validate the metadata against the schema of the table.

        Args:
            table_schema (dict): The schema of the table.

        Returns:
            bool: True if the metadata is valid, False otherwise.
        """
        logger.info("Validating data ingestion metadata", method=VALIDATE)
        for column in table_schema["StorageDescriptor"]["Columns"]:
            if not hasattr(self, column["Name"]):
                logger.error(f"Metadata is missing attribute {column['Name']}")
                return False

        return True

    def write(self) -> None:
        """
        Write the metadata to the metadata bucket.
        """
        logger.info("Writing data ingestion metadata", method=f"{DATA_INGESTION_METADATA}.write")
        try:
            client = boto3.client("s3")
            client.put_object(Body=json.dumps(self), Bucket=self.metadata_bucket, Key=f"{DATA_INGESTION_METADATA_PREFIX}{self.date_time}-{self.ingestion_job_uuid}.json")
            logger.info("Wrote data ingestion metadata", method=f"{DATA_INGESTION_METADATA}.write")
        except Exception as e:
            logger.error("Failed to write data ingestion metadata", method=f"{DATA_INGESTION_METADATA}.write", error_message=str(e))
            raise e
