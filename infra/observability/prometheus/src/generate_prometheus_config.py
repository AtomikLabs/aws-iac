import json
import argparse

def generate_prometheus_config(outputs_file, prometheus_config_file):
    with open(outputs_file) as json_file:
        outputs = json.load(json_file)

    aws_instance_observer_private_ip = outputs['aws_instance_observer_private_ip']['value']
    aws_instance_rabbitmq_private_ips = outputs['aws_instance_rabbitmq_private_ips']['value']

    scrape_configs = [f"""
  - job_name: 'observer'
    static_configs:
      - targets: ['{aws_instance_observer_private_ip}:9100']  # Assuming Node Exporter runs on 9100
"""]

    for ip in aws_instance_rabbitmq_private_ips:
        rabbitmq_job = f"""
  - job_name: 'rabbitmq_{ip}'
    static_configs:
      - targets: ['{ip}:9090']  # Adjust if your RabbitMQ exporter uses a different port
"""
        scrape_configs.append(rabbitmq_job)

    prometheus_config = """global:
  scrape_interval: 30s
scrape_configs:
""" + "".join(scrape_configs)

    with open(prometheus_config_file, 'w') as file:
        file.write(prometheus_config)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate Prometheus configuration from Terraform outputs.')
    parser.add_argument('outputs_file', help='The JSON file containing Terraform outputs.')
    parser.add_argument('prometheus_config_file', help='The output file for the Prometheus configuration.')

    args = parser.parse_args()

    generate_prometheus_config(args.outputs_file, args.prometheus_config_file)
