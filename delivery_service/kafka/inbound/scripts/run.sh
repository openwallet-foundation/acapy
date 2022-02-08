#!/bin/bash
CONTAINER_RUNTIME="${CONTAINER_RUNTIME:-docker}"

ACAPY_NETWORK_NAME=""
ACAPY_RAND_NAME=""
DeliveryServiceArgs=()
EXPOSE_PORT=0
declare -a acapyArgs=($@)
for (( i = 0; i < ${#acapyArgs[*]}; ++ i ))
do
    if [[ "${acapyArgs[$i]}" == "--inbound-queue-transport" || "${acapyArgs[$i]}" == "-iqt" ]]; then
		  EXPOSE_PORT=("${acapyArgs[$i+3]}")
	  fi
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
$CONTAINER_RUNTIME build -t kafka-inbound-delivery-service -f ../delivery_service/kafka/inbound/docker/Dockerfile.run .. || exit 1
$CONTAINER_RUNTIME run --rm -it -d --network $ACAPY_NETWORK_NAME -p "$EXPOSE_PORT:$EXPOSE_PORT" --name "kafka-inbound-delivery-service-runner_${ACAPY_RAND_NAME}" \
    kafka-inbound-delivery-service ${DeliveryServiceArgs[@]}