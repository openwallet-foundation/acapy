#!/bin/bash
CONTAINER_RUNTIME="${CONTAINER_RUNTIME:-docker}"

$CONTAINER_RUNTIME build -t redis-outbound-delivery-service -f ../delivery_service/redis/outbound/docker/Dockerfile.run .. || exit 1

RAND_NAME=$(env LC_ALL=C tr -dc 'a-zA-Z0-9' < /dev/urandom | fold -w 16 | head -n 1)
$CONTAINER_RUNTIME run --rm -it -d --name "redis-outbound-delivery-service-runner_${RAND_NAME}" \
    redis-outbound-delivery-service "$@"