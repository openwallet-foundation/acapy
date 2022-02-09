#!/bin/bash
CONTAINER_RUNTIME="${CONTAINER_RUNTIME:-docker}"

ACAPY_NETWORK_NAME=""
ACAPY_RAND_NAME=""
DeliveryServiceArgs=()
declare -a acapyArgs=($@)
for (( i = 0; i < ${#acapyArgs[*]}; ++ i ))
do
    if [[ "${acapyArgs[$i]}" == "rand-name" ]]; then
        ACAPY_RAND_NAME="${acapyArgs[$i+1]}"
        i=$((i+1))
    elif [[ "${acapyArgs[$i]}" == "network-name" ]]; then
        ACAPY_NETWORK_NAME="${acapyArgs[$i+1]}"
        i=$((i+1))
    else
        DeliveryServiceArgs+=("${acapyArgs[$i]}")
    fi
done
$CONTAINER_RUNTIME build -t redis-outbound-delivery-service -f ../delivery_service/redis/outbound/docker/Dockerfile.run .. || exit 1
if [ -z "$ACAPY_DOCKER_NETWORK" ]; then
    $CONTAINER_RUNTIME run --rm -it -d --name "redis-outbound-delivery-service-runner_${ACAPY_RAND_NAME}" \
    redis-outbound-delivery-service ${DeliveryServiceArgs[@]}
else
    $CONTAINER_RUNTIME run --rm -it -d --network $ACAPY_NETWORK_NAME --name "redis-outbound-delivery-service-runner_${ACAPY_RAND_NAME}" \
    redis-outbound-delivery-service ${DeliveryServiceArgs[@]}
fi