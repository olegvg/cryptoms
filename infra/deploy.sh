#!/bin/bash
set -e

PROJECT_NAME=cryptopay
STAGE=$1
CLUSTER="${PROJECT_NAME}-${STAGE}"
BUILD_VERSION=${BUILD_VERSION:-latest}

function wait_stable {
  declare -a SERVICE_ARNS

  readarray SERVICE_ARNS < <( aws ecs list-services --cluster $1 | jq -r .serviceArns[] )

  if (( ! ${#SERVICE_ARNS[*]} )); then
    echo no services found
    exit 1
  fi

  aws ecs wait services-stable --cluster $1 --services ${SERVICE_ARNS[*]}
}

case $1 in
  staging|production)
#    ./terraform $1 apply -target=aws_ecs_task_definition.pull -var build_version=${BUILD_VERSION} -auto-approve
#    ./ecs-run.sh ${CLUSTER} pull
#    ./terraform $1 apply -target=aws_ecs_task_definition.migrate -var build_version=${BUILD_VERSION} -auto-approve
#    wait_stable ${CLUSTER}
#    ./ecs-run.sh ${CLUSTER} migrate
    ./terraform $1 apply -var build_version=${BUILD_VERSION} -auto-approve
    wait_stable ${CLUSTER}
    ;;
  *)
    echo usage: ./deploy '<staging|production>'
    ;;
esac
