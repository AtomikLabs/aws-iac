import json
import sys
from unittest.mock import mock_open, patch

import pytest

from infra.observability.prometheus.src.generate_prometheus_config import PrometheusConfigGenerator


@pytest.fixture
def args():
    return ["./dummy_outputs.json", "./dummy_prometheus.yml"]


@pytest.fixture
def outputs():
    return {
        "aws_instance_observer_private_ip": {"value": "192.168.0.1"},
        "aws_instance_rabbitmq_private_ips": {"value": ["192.168.0.2", "192.168.0.3"]},
    }


@pytest.fixture
def observer_config():
    return """
    - job_name: 'observer'
        static_configs:
        - targets: ['192.168.0.1:9100']"""


@pytest.fixture
def rabbitmq_config():
    return [
        """
    - job_name: 'rabbitmq_192.168.0.2'
        static_configs:
        - targets: ['192.168.0.2:9090']""",
        """
    - job_name: 'rabbitmq_192.168.0.3'
        static_configs:
        - targets: ['192.168.0.3:9090']""",
    ]


def test_parse_arguments(args):
    with patch("sys.argv", ["program"] + args):
        generator = PrometheusConfigGenerator(sys.argv[1:])
        assert generator.args.outputs_file == args[0]
        assert generator.args.prometheus_config_file == args[1]


def test_load_outputs(args, outputs):
    with patch("builtins.open", mock_open(read_data=json.dumps(outputs)), create=True):
        generator = PrometheusConfigGenerator(args)
        result = generator.load_outputs(args[0])
        assert result == outputs


def test_generate_observer_scrape_config(outputs, observer_config):
    generator = PrometheusConfigGenerator(["", ""])
    result = generator.generate_observer_scrape_config(outputs)
    assert observer_config.strip() in result.strip()


def test_generate_rabbitmq_scrape_configs(outputs, rabbitmq_config):
    generator = PrometheusConfigGenerator(["", ""])
    result = generator.generate_rabbitmq_scrape_configs(outputs)
    result_string = "".join(result).strip()
    for config_block in rabbitmq_config:
        assert config_block.strip() in result_string


def test_generate_prometheus_config(observer_config, rabbitmq_config):
    generator = PrometheusConfigGenerator(["", ""])
    scrape_configs = [observer_config.strip()] + [config.strip() for config in rabbitmq_config]
    config = generator.generate_prometheus_config(scrape_configs)
    assert "global:" in config
    for item in scrape_configs:
        assert item in config


def test_save_prometheus_config(args):
    config_content = "test config"
    with patch("builtins.open", mock_open(), create=True) as mocked_file:
        generator = PrometheusConfigGenerator(args)
        generator.save_prometheus_config(config_content, args[1])
        mocked_file.assert_called_once_with(args[1], "w")
        mocked_file().write.assert_called_once_with(config_content)


def test_run(args, outputs):
    with patch("builtins.open", mock_open(read_data=json.dumps(outputs)), create=True), patch.object(
        PrometheusConfigGenerator, "save_prometheus_config", autospec=True
    ) as mock_save:
        generator = PrometheusConfigGenerator(args)
        generator.run()
        assert mock_save.call_count == 1
