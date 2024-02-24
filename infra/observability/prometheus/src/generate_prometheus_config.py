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
        if not arguments:
            raise ValueError("No arguments provided.")
        parser = argparse.ArgumentParser(description="Generate Prometheus configuration from command line inputs.")
        parser.add_argument("outputs_file", help="The JSON file containing Terraform outputs.")
        parser.add_argument("prometheus_config_file", help="The output file for the Prometheus configuration.")
        parser.add_argument("IPs", help="The IP addresses of instances to be scraped by Prometheus.", nargs="*")
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

        Raises:
            ValueError: If the IP addresses list is empty.
        """
        if not ip_addresses:
            raise ValueError("IP addresses list cannot be empty.")
        scrape_configs = []
        for ip in ip_addresses:
            config = f"""
  - job_name: 'node_exporter_{ip.replace('.', '_')}'
    static_configs:
      - targets: ['{ip}:9100']"""
            scrape_configs.append(config.strip())
        return scrape_configs

    def generate_prometheus_config(self, scrape_configs: list) -> str:
        """
        Generates the complete Prometheus configuration.

        Args:
            scrape_configs: A list of Prometheus scrape configurations.

        Returns:
            A string containing the complete Prometheus configuration.

        Raises:
            ValueError: If the scrape configurations list is empty.
        """
        if not scrape_configs:
            raise ValueError("Scrape configurations cannot be empty.")
        return f"""global:
  scrape_interval: 15s
  evaluation_interval: 15s
scrape_configs:{"".join(scrape_configs)}
"""

    def save_prometheus_config(self, config: str, file_path: str) -> None:
        """
        Saves the generated Prometheus configuration to a file.

        Args:
            config: The Prometheus configuration content.
            file_path: The path to the output file.

        Raises:
            ValueError: If the configuration content or file path is empty.
            IOError: If the file cannot be written to.
        """
        if not config:
            raise ValueError("Configuration content cannot be empty.")
        if not file_path:
            raise ValueError("Configuration file path cannot be empty.")
        try:
            with open(file_path, "w") as file:
                file.write(config)
        except IOError as e:
            raise IOError(f"Failed to write to file {file_path}: {e}")

    def run(self) -> None:
        """
        Executes the configuration generator process.

        Raises:
            TypeError: If the 'args' attribute is not an argparse.Namespace.
            ValueError: If the 'outputs_file' or 'prometheus_config_file' is empty.
        """
        if not isinstance(self.args, argparse.Namespace):
            raise TypeError("Expected 'args' to be an argparse.Namespace.")
        if not self.args.outputs_file or not self.args.prometheus_config_file:
            raise ValueError("File paths cannot be empty.")

        ip_addresses = self.args.IPs
        scrape_configs = self.generate_scrape_configs(ip_addresses)
        prometheus_config = self.generate_prometheus_config(scrape_configs)
        self.save_prometheus_config(prometheus_config, self.args.prometheus_config_file)


if __name__ == "__main__":
    try:
        generator = PrometheusConfigGenerator(sys.argv[1:])
        generator.run()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
