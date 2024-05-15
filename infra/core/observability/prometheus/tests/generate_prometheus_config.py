import json
import sys
from unittest.mock import mock_open, patch

import pytest
from infra.observability.prometheus.src.generate_prometheus_config import PrometheusConfigGenerator


@pytest.fixture
def mock_file_read_data():
    return json.dumps({"observability": {"prometheus": {"scrape_interval": "15s", "evaluation_interval": "15s"}}})


@pytest.fixture
def generator_args():
    return ["./dev-terraform-outputs.json", "prometheus.yml", "--ips", "10.1.1.1", "10.1.2.1"]


@pytest.fixture
def setup_generator(mock_file_read_data, generator_args):
    with (
        patch("builtins.open", mock_open(read_data=mock_file_read_data)),
        patch("sys.argv", ["script.py"] + generator_args),
    ):
        return PrometheusConfigGenerator(sys.argv[1:])


def test_parse_arguments_with_ips(setup_generator):
    generator = setup_generator
    assert generator.args.outputs_file == "./dev-terraform-outputs.json"
    assert generator.args.prometheus_config_file == "prometheus.yml"
    assert generator.args.ips == ["10.1.1.1", "10.1.2.1"]


def test_load_outputs(setup_generator, mock_file_read_data):
    generator = setup_generator
    file_path = "dummy.json"
    with patch(
        "infra.observability.prometheus.src.generate_prometheus_config.open",
        mock_open(read_data=mock_file_read_data),
        create=True,
    ) as mocked_file:
        outputs = generator.load_outputs(file_path)
        expected_outputs = json.loads(mock_file_read_data)
        assert outputs == expected_outputs
        mocked_file.assert_called_once_with(file_path)


def test_generate_scrape_configs(setup_generator):
    generator = setup_generator
    ip_addresses = generator.args.ips
    configs = generator.generate_scrape_configs(ip_addresses)
    assert configs[0].startswith("- job_name: 'node_exporter_10_1_1_1'")
    assert len(configs) == len(ip_addresses)


def test_generate_prometheus_config(setup_generator):
    generator = setup_generator
    scrape_configs = generator.generate_scrape_configs(generator.args.ips)
    config = generator.generate_prometheus_config(scrape_configs)
    assert "scrape_interval: 15s" in config
    assert "evaluation_interval: 15s" in config
    for ip in generator.args.ips:
        assert f"targets: ['{ip}:9100']" in config


def test_save_prometheus_config(setup_generator):
    generator = setup_generator
    config_content = "test config"
    file_path = "test.yml"
    with patch("builtins.open", mock_open()) as mocked_file:
        generator.save_prometheus_config(config_content, file_path)
        mocked_file.assert_called_with(file_path, "w")
        mocked_file().write.assert_called_once_with(config_content)
