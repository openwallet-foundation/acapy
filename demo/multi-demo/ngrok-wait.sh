#!/bin/bash

# based on code developed by Sovrin:  https://github.com/hyperledger/aries-acapy-plugin-toolbox

if [[ "${ACAPY_AGENT_ACCESS}" == "public" ]]; then
    echo "using ngrok end point [$NGROK_NAME]"

    NGROK_ENDPOINT=null
    while [ -z "$NGROK_ENDPOINT" ] || [ "$NGROK_ENDPOINT" = "null" ]
    do
        echo "Fetching end point from ngrok service"
        NGROK_ENDPOINT=$(curl --silent $NGROK_NAME:4040/api/tunnels | ./jq -r '.tunnels[] | select(.proto=="https") | .public_url')

        if [ -z "$NGROK_ENDPOINT" ] || [ "$NGROK_ENDPOINT" = "null" ]; then
            echo "ngrok not ready, sleeping 5 seconds...."
            sleep 5
        fi
    done

    export ACAPY_ENDPOINT=$NGROK_ENDPOINT
fi


echo "Starting aca-py agent with endpoint [$ACAPY_ENDPOINT]"

# ... if you want to echo the aca-py startup command ...
set -x

exec aca-py start \
    --auto-provision \
    --inbound-transport http '0.0.0.0' 8001 \
    --outbound-transport http \
    --genesis-url "http://test.bcovrin.vonx.io/genesis" \
    --endpoint "${ACAPY_ENDPOINT}" \
    --auto-ping-connection \
    --monitor-ping \
    --public-invites \
    --wallet-type "askar" \
    --wallet-name "test_multi" \
    --wallet-key "secret_key" \
    --wallet-storage-type "postgres_storage" \
    --wallet-storage-config "{\"url\":\"wallet-db:5432\",\"max_connections\":5,\"scheme\":\"MultiWalletSingleTable\"}" \
    --wallet-storage-creds "{\"account\":\"DB_USER\",\"password\":\"DB_PASSWORD\",\"admin_account\":\"DB_USER\",\"admin_password\":\"DB_PASSWORD\"}" \
    --admin '0.0.0.0' 8010 \
    --label "test_multi" \
    --admin-insecure-mode \
    --multitenant \
    --multitenant-admin \
    --jwt-secret "very_secret_secret"
