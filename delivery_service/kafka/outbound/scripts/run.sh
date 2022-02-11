#!/bin/bash
CONTAINER_RUNTIME="${CONTAINER_RUNTIME:-docker}"

DELIVERY_SERVICE_NETWORK_NAME=""
ACAPY_RAND_NAME=""
DeliveryServiceArgs=()
declare -a acapyArgs=($@)
for (( i = 0; i < ${#acapyArgs[*]}; ++ i ))
do
    if [[ "${acapyArgs[$i]}" == "rand-name" ]]; then
        ACAPY_RAND_NAME="${acapyArgs[$i+1]}"
        i=$((i+1))
    elif [[ "${acapyArgs[$i]}" == "network-name" ]]; then
        DELIVERY_SERVICE_NETWORK_NAME="${acapyArgs[$i+1]}"
        i=$((i+1))
    else
        DeliveryServiceArgs+=("${acapyArgs[$i]}")
    fi
done
$CONTAINER_RUNTIME build -t kafka-outbound-delivery-service -f ../delivery_service/kafka/outbound/docker/Dockerfile.run .. || exit 1
$CONTAINER_RUNTIME run --rm -it -d --network $DELIVERY_SERVICE_NETWORK_NAME --name "kafka-outbound-delivery-service-runner_${ACAPY_RAND_NAME}" \
    kafka-outbound-delivery-service ${DeliveryServiceArgs[@]}