import sys

import yaml


class ThanosBucketConfigGenerator:
    """
    Generates a Thanos bucket configuration file."""

    def __init__(self, bucket_name, access_key, secret_key, output_file="bucket_config.yml"):
        if not bucket_name:
            raise ValueError("Bucket name cannot be empty.")
        if not access_key:
            raise ValueError("Access key cannot be empty.")
        if not secret_key:
            raise ValueError("Secret key cannot be empty.")
        self.bucket_name = bucket_name
        self.access_key = access_key
        self.secret_key = secret_key
        self.output_file = output_file

    def generate_config_dict(self) -> dict:
        """
        Generates the configuration dictionary.

        Returns:
            dict: The configuration dictionary.
        """
        if not self.bucket_name:
            raise ValueError("Bucket name cannot be empty.")
        if not self.access_key:
            raise ValueError("Access key cannot be empty.")
        if not self.secret_key:
            raise ValueError("Secret key cannot be empty.")
        return {
            "type": "S3",
            "config": {
                "bucket": self.bucket_name,
                "endpoint": "s3.amazonaws.com",
                "access_key": self.access_key,
                "secret_key": self.secret_key,
                "insecure": False,
                "signature_version2": False,
                "encrypt_sse": False,
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

    def save_to_file(self, file_path="bucket_config.yml") -> None:
        """
        Saves the generated configuration to a YAML file.

        Args:
            file_path (str, optional): The file path where the bucket configuration
                should be saved. Defaults to 'bucket_config.yml'.
        """
        if not file_path:
            raise ValueError("File path cannot be empty.")
        config = self.generate_config_dict()
        with open(file_path, "w") as file:
            yaml.dump(config, file, default_flow_style=False)
        print(f"Bucket config generated successfully at '{file_path}'.")


def main(args) -> None:
    """
    Executes the configuration generation process.
    """
    if len(args) != 4:
        print("Usage: <bucket_name> <access_key> <secret_key>")
        sys.exit(1)

    bucket_name, access_key, secret_key, output_file = args
    config_generator = ThanosBucketConfigGenerator(bucket_name, access_key, secret_key)
    config_generator.save_to_file(output_file)


if __name__ == "__main__":
    main(sys.argv[1:])
