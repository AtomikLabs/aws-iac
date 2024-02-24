import argparse
import json
import sys


class PrometheusConfigGenerator:
    """Generates a Prometheus configuration file based on command line arguments."""

    def __init__(self, arguments) -> None:
        """
        Initializes the PrometheusConfigGenerator.

        Args:
            arguments: List of command line arguments.
        """
        self.args = self.parse_arguments(arguments)

    @staticmethod
    def parse_arguments(arguments) -> argparse.Namespace:
        """
        Parses command line arguments.

        Args:
            arguments: List of command line arguments.

        Returns:
            argparse.Namespace: The parsed arguments.

        Raises:
            ValueError: If no arguments are provided.
        """
        parser = argparse.ArgumentParser(description="Generate Prometheus configuration from Terraform outputs.")
        parser.add_argument("outputs_file", help="The JSON file containing Terraform outputs.")
        parser.add_argument("prometheus_config_file", help="The output file for the Prometheus configuration.")
        if not arguments:
            raise ValueError("No arguments provided.")
        return parser.parse_args(arguments)

    def load_outputs(self, file_path: str) -> dict:
        """
        Loads Terraform outputs from a specified JSON file.

        Args:
            file_path: The path to the JSON file containing Terraform outputs.

        Returns:
            dict: The loaded Terraform outputs.

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

    def generate_observer_scrape_config(self, outputs: dict) -> str:
        """
        Generates the Prometheus scrape configuration for the observer.

        Args:
            outputs: The Terraform outputs.

        Returns:
            str: The Prometheus scrape configuration for the observer.

        Raises:
            TypeError: If the outputs are not a dictionary.
            ValueError: If the observer IP address is not found in the outputs.
        """
        if not isinstance(outputs, dict):
            raise TypeError("Expected 'outputs' to be a dictionary.")
        attribute_name = "aws_instance_observer_private_ip"
        if attribute_name not in outputs:
            raise ValueError(f"'{attribute_name}' not found in outputs.")
        observer_ip = outputs.get(attribute_name, {}).get("value")
        if not observer_ip:
            raise ValueError("Observer IP address not found in outputs.")
        observer_config = f"""
    - job_name: 'observer'
        static_configs:
        - targets: ['{observer_ip}:9100']"""
        return observer_config

    def generate_rabbitmq_scrape_configs(self, outputs: dict) -> list:
        """
        Generates the Prometheus scrape configurations for RabbitMQ instances.

        Args:
            outputs: The Terraform outputs.

        Returns:
            list: The Prometheus scrape configurations for RabbitMQ instances.

        Raises:
            TypeError: If the outputs are not a dictionary.
            ValueError: If the RabbitMQ IP addresses are not found in the outputs.
        """
        if not isinstance(outputs, dict):
            raise TypeError("Expected 'outputs' to be a dictionary.")
        attribute_name = "aws_instance_rabbitmq_private_ips"
        if attribute_name not in outputs:
            raise ValueError(f"'{attribute_name}' not found in outputs.")
        rabbitmq_ips = outputs.get("aws_instance_rabbitmq_private_ips", {}).get("value", [])
        if not rabbitmq_ips:
            raise ValueError("RabbitMQ IP addresses not found in the outputs.")

        rabbitmq_configs = []
        for ip in rabbitmq_ips:
            config = f"""
    - job_name: 'rabbitmq_{ip}'
        static_configs:
        - targets: ['{ip}:9090']"""
            rabbitmq_configs.append(config)

        return rabbitmq_configs

    def generate_prometheus_config(self, scrape_configs: list) -> str:
        """
        Generates the complete Prometheus configuration.

        Args:
            scrape_configs: The list of scrape configurations.

        Returns:
            str: The complete Prometheus configuration.

        Raises:
            ValueError: If the scrape configurations are empty.
        """
        if not scrape_configs:
            raise ValueError("Scrape configurations cannot be empty.")
        return f"""global:
  scrape_interval: 30s
scrape_configs:
{''.join(scrape_configs)}
"""

    def save_prometheus_config(self, config: str, file_path: str) -> None:
        """
        Saves the generated Prometheus configuration to a specified file.

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
        print(f"Prometheus config generated successfully at '{file_path}'.")

    def run(self):
        """
        Runs the Prometheus configuration generator.

        Raises:
            TypeError: If the arguments are not of the expected types.
            ValueError: If the file paths are empty.
        """
        if not isinstance(self.args, argparse.Namespace):
            raise TypeError("Expected 'args' to be an argparse.Namespace.")
        if not isinstance(self.args.outputs_file, str):
            raise TypeError("Expected 'outputs_file' to be a string.")
        if not self.args.outputs_file:
            raise ValueError("File path cannot be empty.")
        if not isinstance(self.args.prometheus_config_file, str):
            raise TypeError("Expected 'prometheus_config_file' to be a string.")
        if not self.args.prometheus_config_file:
            raise ValueError("File path cannot be empty.")

        outputs = self.load_outputs(self.args.outputs_file)
        scrape_configs = [self.generate_observer_scrape_config(outputs)]
        scrape_configs += self.generate_rabbitmq_scrape_configs(outputs)
        prometheus_config = self.generate_prometheus_config(scrape_configs)
        self.save_prometheus_config(prometheus_config, self.args.prometheus_config_file)


if __name__ == "__main__":
    generator = PrometheusConfigGenerator(sys.argv[1:])
    generator.run()
