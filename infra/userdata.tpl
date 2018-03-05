#!/bin/bash
cat <<EOF > /etc/ecs/ecs.config
ECS_CLUSTER=${cluster_name}
ECS_ENGINE_AUTH_TYPE=dockercfg
ECS_CONTAINER_STOP_TIMEOUT=5s
ECS_ENGINE_AUTH_DATA={"docker.cryptology.com":{"auth":"${docker_registry_auth}"}}
ECS_AVAILABLE_LOGGING_DRIVERS=["json-file","awslogs"]
EOF
yum update -y ecs-init
