FROM apache/airflow:2.9.0

USER root

RUN apt-get update && apt-get install -y awscli python3-pip \
    && apt-get clean

RUN pip3 install --upgrade pip && pip3 install wheel

COPY /home/ec2-user/dags/requirements.txt /home/ec2-user/requirements.txt

RUN pip3 install -r /home/ec2-user/requirements.txt

USER airflow