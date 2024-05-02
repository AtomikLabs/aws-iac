import os

from dotenv import load_dotenv
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError, KafkaError

load_dotenv("/data/kafka/.env")


def create_topics():
    admin_client = KafkaAdminClient(bootstrap_servers=[f"${os.getenv('ORCHESTRATION_HOST_PRIVATE_IP')}:9092"])

    topic_list = [
        NewTopic(name="data_arxiv_summaries_ingestion_complete", num_partitions=1, replication_factor=1),
    ]

    for topic in topic_list:
        try:
            admin_client.create_topics(new_topics=[topic], validate_only=False)
            print(f"Topic {topic.name} created successfully.")
        except TopicAlreadyExistsError:
            print(f"Topic {topic.name} already exists.")
        except KafkaError as e:
            print(f"Error creating topic {topic.name}: {str(e)}")

    admin_client.close()


if __name__ == "__main__":
    create_topics()
