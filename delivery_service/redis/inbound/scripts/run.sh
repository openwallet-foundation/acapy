#!/bin/bash
CONTAINER_RUNTIME="${CONTAINER_RUNTIME:-docker}"

DELIVERY_SERVICE_NETWORK_NAME=""
ACAPY_RAND_NAME=""
DeliveryServiceArgs=()
EXPOSE_PORTS=()
declare -a acapyArgs=($@)
for (( i = 0; i < ${#acapyArgs[*]}; ++ i ))
do
    if [[ "${acapyArgs[$i]}" == "--inbound-queue-transport" || "${acapyArgs[$i]}" == "-iqt" ]]; then
		  EXPOSE_PORTS+=("${acapyArgs[$i+3]}")
	  fi
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
EXPOSE_PORTS_CMD=""
for (( i = 0; i < ${#EXPOSE_PORTS[*]}; ++ i ))
do
  if [[ $i == 0 ]]; then
    EXPOSE_PORTS_CMD+="-p ${EXPOSE_PORTS[$i]}:${EXPOSE_PORTS[$i]}"
  else
      EXPOSE_PORTS_CMD+=" -p ${EXPOSE_PORTS[$i]}:${EXPOSE_PORTS[$i]}"
  fi
done
$CONTAINER_RUNTIME build -t redis-inbound-delivery-service -f ../delivery_service/redis/inbound/docker/Dockerfile.run .. || exit 1
if [ -z "$ACAPY_DOCKER_NETWORK" ]; then
    $CONTAINER_RUNTIME run --rm -it -d ${EXPOSE_PORTS_CMD[@]} --name "redis-inbound-delivery-service-runner_${ACAPY_RAND_NAME}" \
    redis-inbound-delivery-service ${DeliveryServiceArgs[@]}
else
    $CONTAINER_RUNTIME run --rm -it -d --network $DELIVERY_SERVICE_NETWORK_NAME ${EXPOSE_PORTS_CMD[@]} --name "redis-inbound-delivery-service-runner_${ACAPY_RAND_NAME}" \
    redis-inbound-delivery-service ${DeliveryServiceArgs[@]}
fi