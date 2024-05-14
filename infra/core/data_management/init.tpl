#!/bin/bash

yum install docker -y
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

target=$(readlink -f /dev/sdh)
if sudo file -s "$target" | grep -q "ext"; then
  echo "Filesystem exists on target"
else
  /usr/sbin/mkfs.ext4 /dev/sdh
fi

mount /dev/sdh /neo4j
mkdir -p /neo4j/data
mkdir -p /neo4j/logs
mkdir /neo4j/plugins
pushd /neo4j/plugins
wget https://github.com/neo4j-contrib/neo4j-apoc-procedures/releases/download/4.1.0.11/apoc-4.1.0.11-all.jar
popd

chown :docker /neo4j/data /neo4j/logs /neo4j/plugins
chmod g+rwx /neo4j/data /neo4j/logs /neo4j/plugins

docker run --restart=always \
--memory=6g \
--cpus=2 \
-p 7474:7474 -p 7687:7687 \
-v /neo4j/data:/data \
-v /neo4j/logs:/logs \
-v /neo4j/plugins:/plugins \
-e NEO4J_AUTH=${neo4j_username}/${neo4j_password} \
-e NEO4J_dbms_security_procedures_unrestricted=apoc.\\\* \
--name neo4j \
neo4j:4.1