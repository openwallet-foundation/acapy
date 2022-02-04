#!/bin/bash
CONTAINER_RUNTIME="${CONTAINER_RUNTIME:-docker}"

$CONTAINER_RUNTIME build -t redis-inbound-delivery-service -f ../delivery_service/redis/inbound/docker/Dockerfile.run .. || exit 1

EXPOSE_PORT=0
declare -a inboundArgs=($@)
for (( i = 0; i < ${#acapyArgs[*]}; ++ i ))
do
    if [[ "${acapyArgs[$i]}" == "--inbound-queue-transport" || "${acapyArgs[$i]}" == "-iqt" ]]; then
		EXPOSE_PORT=("${acapyArgs[$i+3]}")
	fi
done
RAND_NAME=$(env LC_ALL=C tr -dc 'a-zA-Z0-9' < /dev/urandom | fold -w 16 | head -n 1)
$CONTAINER_RUNTIME run --rm -it -d -p "$EXPOSE_PORT:$EXPOSE_PORT" --name "redis-inbound-delivery-service-runner_${RAND_NAME}" \
    redis-inbound-delivery-service "$@"