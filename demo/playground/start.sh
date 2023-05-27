#!/bin/bash

# set -euxo pipefail

# if $TUNNEL_NAME is not empty, grab the service's ngrok route and set our ACAPY_ENDPOINT
if [[ ! -z "$TUNNEL_NAME" ]]; then
    echo "using ngrok tunnel for [$TUNNEL_NAME]"

    NGROK_ENDPOINT=null
    while [ -z "$NGROK_ENDPOINT" ] || [ "$NGROK_ENDPOINT" = "null" ]
    do
        echo "Fetching end point from ngrok service"
        NGROK_ENDPOINT=$(curl -s $TUNNEL_HOST:4040/api/tunnels | jq -r '.tunnels[] | select(.name==env.TUNNEL_NAME) | select(.proto=="https") | .public_url')

        if [ -z "$NGROK_ENDPOINT" ] || [ "$NGROK_ENDPOINT" = "null" ]; then
            echo "ngrok not ready, sleeping 5 seconds...."
            sleep 5
        fi
    done

    export ACAPY_ENDPOINT=$NGROK_ENDPOINT
fi


echo "Starting aca-py agent [$AGENT_LABEL] with endpoint [$ACAPY_ENDPOINT]"

# ... if you want to echo the aca-py startup command ...
# set -x

aca-py start \
    --auto-provision \
    --arg-file ${AGENT_ARG_FILE} \
    --label "${AGENT_LABEL}" \
    --inbound-transport http 0.0.0.0 ${AGENT_HTTP_IN_PORT} \
    --outbound-transport http \
    --emit-new-didcomm-prefix \
    --wallet-type askar \
    --wallet-storage-type postgres_storage \
    --admin-insecure-mode \
    --admin 0.0.0.0 ${AGENT_HTTP_ADMIN_PORT} \
    --endpoint "${ACAPY_ENDPOINT}"
