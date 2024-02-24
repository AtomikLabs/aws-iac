import json
import sys
from unittest.mock import mock_open, patch

import pytest

from infra.observability.prometheus.src.generate_prometheus_config import PrometheusConfigGenerator


@pytest.fixture
def args_with_ips():
    return ["./dummy_outputs.json", "./dummy_prometheus.yml", "192.168.1.1", "192.168.1.2"]


@pytest.fixture
def ip_addresses():
    return ["192.168.1.1", "192.168.1.2"]


@pytest.fixture
def expected_scrape_configs():
    return [
        "- job_name: 'node_exporter_192_168_1_1'\n    static_configs:\n      - targets: ['192.168.1.1:9100']",
        "- job_name: 'node_exporter_192_168_1_2'\n    static_configs:\n      - targets: ['192.168.1.2:9100']"
    ]


def test_parse_arguments_with_ips(args_with_ips):
    with patch("sys.argv", ["program"] + args_with_ips):
        generator = PrometheusConfigGenerator(sys.argv[1:])
        assert generator.args.outputs_file == args_with_ips[0]
        assert generator.args.prometheus_config_file == args_with_ips[1]
        assert generator.args.IPs == args_with_ips[2:]


def test_generate_scrape_configs(ip_addresses, expected_scrape_configs):
    generator = PrometheusConfigGenerator(["", "", *ip_addresses])
    result = generator.generate_scrape_configs(ip_addresses)
    for expected, actual in zip(expected_scrape_configs, result):
        assert expected == actual


def test_generate_prometheus_config(expected_scrape_configs):
    generator = PrometheusConfigGenerator(["", ""])
    config = generator.generate_prometheus_config(expected_scrape_configs)
    assert "global:" in config
    for item in expected_scrape_configs:
        assert item in config


def test_save_prometheus_config(args_with_ips):
    config_content = "test config"
    with patch("builtins.open", mock_open(), create=True) as mocked_file:
        generator = PrometheusConfigGenerator(args_with_ips)
        generator.save_prometheus_config(config_content, args_with_ips[1])
        mocked_file.assert_called_once_with(args_with_ips[1], "w")
        mocked_file().write.assert_called_once_with(config_content)


def test_run_calls_correct_methods_with_expected_arguments(args_with_ips, ip_addresses):
    with patch("infra.observability.prometheus.src.generate_prometheus_config.PrometheusConfigGenerator.generate_scrape_configs", autospec=True) as mock_generate_scrape_configs, \
         patch("infra.observability.prometheus.src.generate_prometheus_config.PrometheusConfigGenerator.save_prometheus_config", autospec=True) as mock_save, \
         patch("builtins.open", mock_open(read_data=json.dumps({})), create=True):

        generator = PrometheusConfigGenerator(args_with_ips)
        generator.run()

        mock_generate_scrape_configs.assert_called_once_with(generator, ip_addresses)

        mock_save.assert_called()
