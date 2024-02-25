import pytest
import json
from unittest.mock import mock_open, patch, MagicMock

from infra.observability.prometheus.src.generate_prometheus_config import PrometheusConfigGenerator


@pytest.fixture
def args():
    return ["dummy.json", "prometheus.yml", "--ips", "10.0.1.1", "10.0.2.2"]


@pytest.fixture
def outputs():
    return {"aws_instance_prometheus_private_ip": {"value": "10.0.1.1"}}


@pytest.fixture
def mock_args(mocker):
    return mocker.patch("argparse.ArgumentParser.parse_args",
                        return_value=MagicMock(outputs_file="dummy.json",
                                               prometheus_config_file="prometheus.yml",
                                               ips=["10.0.1.1", "10.0.2.2"]))


def test_load_outputs(mock_args, outputs):
    with patch("builtins.open", mock_open(read_data=json.dumps(outputs)), create=True) as mocked_file:
        generator = PrometheusConfigGenerator([])
        result = generator.load_outputs("dummy.json")
        mocked_file.assert_called_once_with("dummy.json")
        assert result == outputs


def test_generate_scrape_configs(mock_args):
    ip_addresses = ["10.0.1.1", "10.0.2.2"]
    generator = PrometheusConfigGenerator([])
    result = generator.generate_scrape_configs(ip_addresses)
    assert len(result) == 2
    assert "10.0.1.1:9100" in result[0]
    assert "10.0.2.2:9100" in result[1]


def test_generate_prometheus_config(mock_args):
    scrape_configs = ["- job_name: 'node_exporter_10_0_1_1'\n  static_configs:\n    - targets: ['10.0.1.1:9100']"]
    generator = PrometheusConfigGenerator([])
    result = generator.generate_prometheus_config(scrape_configs)
    assert "scrape_configs:" in result
    assert "10.0.1.1:9100" in result


def test_save_prometheus_config(mock_args):
    config = "global:\n  scrape_interval: 15s"
    with patch("builtins.open", mock_open(), create=True) as mocked_file:
        generator = PrometheusConfigGenerator([])
        generator.save_prometheus_config(config, "prometheus.yml")
        mocked_file.assert_called_once_with("prometheus.yml", "w")
        mocked_file().write.assert_called_once_with(config)


def test_run(mock_args, outputs):
    with patch("builtins.open", mock_open(read_data=json.dumps(outputs)), create=True), \
         patch.object(PrometheusConfigGenerator, "save_prometheus_config") as mock_save:
        generator = PrometheusConfigGenerator([])
        generator.run()
        mock_save.assert_called()
