provider "kafka" {
    bootstrap_servers = ["${aws_instance.orchestration_host.private_ip}:9092"]
}

  # **********************************************************
  # * DATA INGESTION                                         *
  # **********************************************************

resource "kafka_topic" "data-arxiv_summaries-ingestion-complete" {
    name                = "data-arxiv_summaries-ingestion-complete"
    replication_factor  = 1
    partitions          = 1
}