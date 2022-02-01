#!/bin/bash
CONTAINER_RUNTIME="${CONTAINER_RUNTIME:-docker}"

$CONTAINER_RUNTIME build -t redis-inbound-delivery-service -f ../delivery_service/redis/inbound/docker/Dockerfile.run .. || exit 1

RAND_NAME=$(env LC_ALL=C tr -dc 'a-zA-Z0-9' < /dev/urandom | fold -w 16 | head -n 1)
$CONTAINER_RUNTIME run --rm -it -d --name "redis-inbound-delivery-service-runner_${RAND_NAME}" \
    redis-inbound-delivery-service "$@"