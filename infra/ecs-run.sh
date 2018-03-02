#!/bin/bash
set -e

declare -r CLUSTER=$1
declare -r TASK_FAMILY=$2
declare -i COUNT=$3
declare -a TASK_ARNS
declare -a EXIT_CODES
declare -i TASK_VERSION

if (( ! ${COUNT} )); then
  COUNT=1
fi

if [ -z "${CLUSTER}" ]; then
  echo first arg must be cluster name
  exit 1
fi

if [ -z "${TASK_FAMILY}" ]; then
  echo second arg must be task family name
  exit 1
fi

echo about to run ${COUNT} ${TASK_FAMILY} on ${CLUSTER}

TASK_VERSION=$( aws ecs describe-task-definition --task-definition ${CLUSTER}-${TASK_FAMILY} | \
                jq -r .taskDefinition.revision )
if (( ! ${TASK_VERSION} )); then
  echo cant get task version
  exit 1
fi

echo version is ${TASK_VERSION}

readarray TASK_ARNS < <( aws ecs run-task --count ${COUNT} \
                                          --cluster ${CLUSTER} \
                                          --placement-strategy $(jo -a $(jo field=instanceId type=spread)) \
                                          --task-definition ${CLUSTER}-${TASK_FAMILY}:${TASK_VERSION} | \
                         jq -r .tasks[].taskArn )

if (( $COUNT != ${#TASK_ARNS[@]} )); then
  echo requested to run ${COUNT} tasks, aws is running ${#TASK_ARNS[@]}:
  printf \\t%s\\n ${TASK_ARNS[*]}
  exit 1
fi

echo task arns:
printf \\t%s\\n ${TASK_ARNS[*]}

echo wait for tasks to stop
aws ecs wait tasks-stopped --cluster ${CLUSTER} --tasks ${TASK_ARNS[*]}

readarray EXIT_CODES < <( aws ecs describe-tasks --cluster ${CLUSTER} --tasks ${TASK_ARNS[*]} | \
                          jq -r .tasks[].containers[].exitCode )

LOG_GROUP_NAME=$( aws ecs describe-task-definition --task-definition ${CLUSTER}-${TASK_FAMILY}:${TASK_VERSION} | \
                  jq -r '.taskDefinition.containerDefinitions[0].logConfiguration.options["awslogs-group"]' )

if [ "${LOG_GROUP_NAME}" != "null" ]; then
  LOG_STREAM_NAME=$( aws logs describe-log-streams --order-by LastEventTime --descending --log-group-name ${LOG_GROUP_NAME} | \
                     jq -r .logStreams[0].logStreamName )
  echo CONTAINER LOGS
  aws logs get-log-events --log-group-name ${LOG_GROUP_NAME} --log-stream-name ${LOG_STREAM_NAME} | jq -r .events[].message
fi

for EXIT_CODE in ${EXIT_CODES[*]}; do
  if (( $EXIT_CODE != 0 )); then
    exit ${EXIT_CODE}
  fi
done

echo done
exit 0
