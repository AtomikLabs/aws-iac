FROM apache/airflow:2.9.0

USER root
RUN apt-get update && apt-get install -y awscli \
    && apt-get clean

USER airflow
