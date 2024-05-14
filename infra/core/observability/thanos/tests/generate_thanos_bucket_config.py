from unittest import mock
from unittest.mock import call, mock_open, patch

import pytest
from infra.observability.thanos.src.generate_thanos_bucket_config import ThanosBucketConfigGenerator


@pytest.fixture
def generator_args():
    return ["test-bucket", "test-access-key", "test-secret-key", "./temp/bucket_config.yml"]


@pytest.fixture
def generator(generator_args):
    return ThanosBucketConfigGenerator(*generator_args)


def test_generate_config_dict(generator, generator_args):
    expected_config = {
        "type": "S3",
        "config": {
            "bucket": generator_args[0],
            "endpoint": "s3.amazonaws.com",
            "access_key": generator_args[1],
            "secret_key": generator_args[2],
            "insecure": False,
            "signature_version2": False,
            "put_user_metadata": {},
            "http_config": {
                "idle_conn_timeout": "90s",
                "response_header_timeout": "2m",
                "insecure_skip_verify": False,
            },
            "trace": {
                "enable": False,
            },
            "part_size": 134217728,
        },
    }
    assert generator.generate_config_dict() == expected_config


@pytest.mark.parametrize("file_path", ["custom_path.yml"])
def test_save_to_file(generator, file_path):
    with patch("builtins.open", mock_open()) as mocked_file:
        generator.save_to_file(file_path)
        mocked_file.assert_called_once_with(file_path, "w")


@patch("yaml.dump", autospec=True)
def test_yaml_dump_called_with_correct_arguments(mock_yaml_dump, generator):
    config_dict = generator.generate_config_dict()
    file_path = "bucket_config.yml"
    with patch("builtins.open", mock_open()):
        generator.save_to_file(file_path)
        expected_call = call(config_dict, mock.ANY, default_flow_style=False)
        mock_yaml_dump.assert_has_calls([expected_call])


def test_invalid_bucket_name_raises_error():
    with pytest.raises(ValueError):
        ThanosBucketConfigGenerator("", "access-key", "secret-key")


def test_invalid_access_key_raises_error():
    with pytest.raises(ValueError):
        ThanosBucketConfigGenerator("bucket-name", "", "secret-key")


def test_invalid_secret_key_raises_error():
    with pytest.raises(ValueError):
        ThanosBucketConfigGenerator("bucket-name", "access-key", "")
