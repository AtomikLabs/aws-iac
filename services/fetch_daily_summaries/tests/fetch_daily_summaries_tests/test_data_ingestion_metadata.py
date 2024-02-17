import pytest

from services.fetch_daily_summaries.src.data_ingestion_metadata import DataIngestionMetadata


@pytest.fixture
def mock_boto3(mocker):
    return mocker.patch('boto3.client')


@pytest.fixture
def mock_logger(mocker):
    return mocker.patch('services.fetch_daily_summaries.src.data_ingestion_metadata.logger')


def test_get_schema(mock_boto3, mock_logger):
    database_name = "TestDB"
    table_name = "TestTable"
    metadata = DataIngestionMetadata()
    metadata.get_schema(database_name, table_name)
    mock_boto3.assert_called_with("glue")
    mock_logger.info.assert_called_with(
        "Getting data ingestion metadata schema",
        database_name=database_name,
        table_name=table_name,
        method="DataIngestionMetadata.get_schema",
    )


@pytest.fixture
def metadata_instance():
    metadata = DataIngestionMetadata()
    metadata.database_name = "test_database"
    metadata.table_name = "test_table"
    return metadata


@pytest.fixture
def valid_table_schema():
    return {
        "StorageDescriptor": {
            "Columns": [
                {"Name": "app_name", "Type": "string"},
            ]
        }
    }


def test_validate_success(metadata_instance, valid_table_schema, mocker):
    mocker.patch.object(metadata_instance, 'get_schema', return_value=valid_table_schema)

    assert metadata_instance.validate(), "Validation should pass with a matching schema"


def test_validate_failure_missing_attribute(metadata_instance, mocker):
    invalid_table_schema = {
        "StorageDescriptor": {
            "Columns": [
                {"Name": "missing_attribute", "Type": "string"},
            ]
        }
    }
    mocker.patch.object(metadata_instance, 'get_schema', return_value=invalid_table_schema)

    assert not metadata_instance.validate(), "Validation should fail due to missing attribute"


def test_validate_error_no_database_or_table_name(mocker):
    metadata = DataIngestionMetadata()
    mocker.patch('services.fetch_daily_summaries.src.data_ingestion_metadata.logger')

    with pytest.raises(ValueError, match="Database name and table name must be set"):
        metadata.validate()


@pytest.mark.parametrize("exception", [Exception("Test error")])
def test_write_failure(mock_boto3, mock_logger, exception):
    metadata = DataIngestionMetadata()
    mock_boto3.side_effect = exception
    with pytest.raises(Exception) as exc_info:
        metadata.write()
    assert str(exc_info.value) == "Test error"
    mock_logger.error.assert_called_with(
        "Failed to write data ingestion metadata",
        method="DataIngestionMetadata.write",
        error_message=str(exception),
    )


def test_set_app_name():
    metadata = DataIngestionMetadata()
    metadata.app_name = "test_app"
    assert metadata.app_name == "test_app"
    with pytest.raises(ValueError):
        metadata.app_name = 123


def test_set_date_time():
    metadata = DataIngestionMetadata()
    metadata.date_time = "2021-01-01T00:00:00"
    assert metadata.date_time == "2021-01-01T00:00:00"
    with pytest.raises(ValueError):
        metadata.date_time = 123


def test_set_data_source():
    metadata = DataIngestionMetadata()
    metadata.data_source = "test_source"
    assert metadata.data_source == "test_source"
    with pytest.raises(ValueError):
        metadata.data_source = 123


def test_set_database_name():
    metadata = DataIngestionMetadata()
    metadata.database_name = "test_db"
    assert metadata.database_name == "test_db"
    with pytest.raises(ValueError):
        metadata.database_name = 123


def test_set_environment():
    metadata = DataIngestionMetadata()
    metadata.environment = "test"
    assert metadata.environment == "test"
    with pytest.raises(ValueError):
        metadata.environment = 123


def test_set_error_message():
    metadata = DataIngestionMetadata()
    metadata.error_message = "test_error"
    assert metadata.error_message == "test_error"
    with pytest.raises(ValueError):
        metadata.error_message = 123


def test_set_function_name():
    metadata = DataIngestionMetadata()
    metadata.function_name = "test_function"
    assert metadata.function_name == "test_function"
    with pytest.raises(ValueError):
        metadata.function_name = 123


def test_set_location_raw_data_saved():
    metadata = DataIngestionMetadata()
    metadata.location_raw_data_saved = "test_location"
    assert metadata.location_raw_data_saved == "test_location"
    with pytest.raises(ValueError):
        metadata.location_raw_data_saved = 123


def test_set_metadata_bucket():
    metadata = DataIngestionMetadata()
    metadata.metadata_bucket = "test_bucket"
    assert metadata.metadata_bucket == "test_bucket"
    with pytest.raises(ValueError):
        metadata.metadata_bucket = 123


def test_set_original_data_format():
    metadata = DataIngestionMetadata()
    metadata.original_data_format = "test_format"
    assert metadata.original_data_format == "test_format"
    with pytest.raises(ValueError):
        metadata.original_data_format = 123


def test_set_raw_data_bucket():
    metadata = DataIngestionMetadata()
    metadata.raw_data_bucket = "test_bucket"
    assert metadata.raw_data_bucket == "test_bucket"
    with pytest.raises(ValueError):
        metadata.raw_data_bucket = 123


def test_set_raw_data_key():
    metadata = DataIngestionMetadata()
    metadata.raw_data_key = "test_key"
    assert metadata.raw_data_key == "test_key"
    with pytest.raises(ValueError):
        metadata.raw_data_key = 123


def test_set_size_of_data_downloaded():
    metadata = DataIngestionMetadata()
    metadata.size_of_data_downloaded = 123
    assert metadata.size_of_data_downloaded == 123
    with pytest.raises(ValueError):
        metadata.size_of_data_downloaded = "test"


def test_set_status():
    metadata = DataIngestionMetadata()
    metadata.status = "test_status"
    assert metadata.status == "test_status"
    with pytest.raises(ValueError):
        metadata.status = 123


def test_set_stored_data_format():
    metadata = DataIngestionMetadata()
    metadata.stored_data_format = "test_format"
    assert metadata.stored_data_format == "test_format"
    with pytest.raises(ValueError):
        metadata.stored_data_format = 123


def test_set_table_name():
    metadata = DataIngestionMetadata()
    metadata.table_name = "test_table"
    assert metadata.table_name == "test_table"
    with pytest.raises(ValueError):
        metadata.table_name = 123


def test_set_triggered_functions():
    metadata = DataIngestionMetadata()
    metadata.triggered_functions = ["test_function"]
    assert metadata.triggered_functions == ["test_function"]
    with pytest.raises(ValueError):
        metadata.triggered_functions = "test_function"


def test_set_uri():
    metadata = DataIngestionMetadata()
    metadata.uri = "test_uri"
    assert metadata.uri == "test_uri"
    with pytest.raises(ValueError):
        metadata.uri = 123