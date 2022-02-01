#!/bin/bash
CONTAINER_RUNTIME="${CONTAINER_RUNTIME:-docker}"

$CONTAINER_RUNTIME build -t kafka-outbound-delivery-service -f ../delivery_service/kafka/outbound/docker/Dockerfile.run .. || exit 1

RAND_NAME=$(env LC_ALL=C tr -dc 'a-zA-Z0-9' < /dev/urandom | fold -w 16 | head -n 1)
$CONTAINER_RUNTIME run --rm -it -d --name "kafka-outbound-delivery-service-runner_${RAND_NAME}" \
    kafka-outbound-delivery-service "$@"