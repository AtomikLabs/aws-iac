import argparse
import json
import sys


class PrometheusConfigGenerator:
    """
    Generates a Prometheus configuration file based on command line arguments.
    """

    def __init__(self, arguments) -> None:
        """
        Initializes the PrometheusConfigGenerator with command line arguments.
        """
        self.args = self.parse_arguments(arguments)
        with open("./.atomiklabs.json", "r") as file:
            data = json.load(file)
            self._scrape_interval = data["observability"]["prometheus"]["scrape_interval"]
            self._evaluation_interval = data["observability"]["prometheus"]["evaluation_interval"]
            if not self._scrape_interval:
                raise ValueError("Scrape interval cannot be empty. Check the .atomiklabs.json file.")
            if not self._evaluation_interval:
                raise ValueError("Evaluation interval cannot be empty. Check the .atomiklabs.json file")

    @staticmethod
    def parse_arguments(arguments) -> argparse.Namespace:
        """
        Parses command line arguments.

        Args:
            arguments: A list of command line arguments.

        Returns:
            An argparse.Namespace object containing the parsed arguments.

        Raises:
            ValueError: If no arguments are provided.
        """
        parser = argparse.ArgumentParser(description="Generate Prometheus configuration from command line inputs.")
        parser.add_argument("outputs_file", help="The JSON file containing Terraform outputs.")
        parser.add_argument("prometheus_config_file", help="The output file for the Prometheus configuration.")
        parser.add_argument(
            "--ips", nargs="+", help="The IP addresses of instances to be scraped by Prometheus.", required=True
        )
        return parser.parse_args(arguments)

    def load_outputs(self, file_path: str) -> dict:
        """
        Loads Terraform outputs from a JSON file.

        Args:
            file_path: The path to the JSON file containing Terraform outputs.

        Returns:
            A dictionary containing the Terraform outputs.

        Raises:
            ValueError: If the file path is empty.
            FileNotFoundError: If the file is not found.
            json.JSONDecodeError: If the file cannot be decoded as JSON.
        """
        if not file_path:
            raise ValueError("File path cannot be empty.")
        try:
            with open(file_path) as json_file:
                return json.load(json_file)
        except FileNotFoundError:
            raise FileNotFoundError(f"File {file_path} not found.")
        except json.JSONDecodeError:
            raise json.JSONDecodeError(f"Error decoding JSON from {file_path}.")

    def generate_scrape_configs(self, ip_addresses: list) -> list:
        """
        Generates Prometheus scrape configurations for specified IP addresses.

        Args:
            ip_addresses: A list of IP addresses to be scraped by Prometheus.

        Returns:
            A list of Prometheus scrape configurations.
        """
        if not ip_addresses:
            raise ValueError("IP addresses list cannot be empty.")
        scrape_configs = []
        for ip in ip_addresses:
            if ip.lower() != "null":
                config = f"""
  - job_name: 'node_exporter_{ip.replace('.', '_')}'
  static_configs:
    - targets: ['{ip}:9100']"""
                scrape_configs.append(config.strip() + "\n")
        return scrape_configs

    def generate_prometheus_config(self, scrape_configs: list) -> str:
        """
        Generates the complete Prometheus configuration.

        Args:
            scrape_configs: A list of Prometheus scrape configurations.

        Returns:
            A string containing the complete Prometheus configuration.
        """
        if not scrape_configs:
            raise ValueError("Scrape configurations cannot be empty.")
        return f"""global:
  external_labels:
    prometheus: 'prometheus_one'
  scrape_interval: {self._scrape_interval}
  evaluation_interval: {self._evaluation_interval}
scrape_configs:
{"".join(scrape_configs)}
"""

    def save_prometheus_config(self, config: str, file_path: str) -> None:
        """
        Saves the generated Prometheus configuration to a file.

        Args:
            config: The Prometheus configuration content.
            file_path: The path to the output file.

        Raises:
            ValueError: If the configuration content or file path is empty.
        """
        if not config:
            raise ValueError("Configuration content cannot be empty.")
        if not file_path:
            raise ValueError("Configuration file path cannot be empty.")
        with open(file_path, "w") as file:
            file.write(config)

    def run(self) -> None:
        """
        Executes the configuration generator process.
        """
        ip_addresses = self.args.ips
        scrape_configs = self.generate_scrape_configs(ip_addresses)
        prometheus_config = self.generate_prometheus_config(scrape_configs)
        self.save_prometheus_config(prometheus_config, self.args.prometheus_config_file)


if __name__ == "__main__":
    generator = PrometheusConfigGenerator(sys.argv[1:])
    generator.run()
