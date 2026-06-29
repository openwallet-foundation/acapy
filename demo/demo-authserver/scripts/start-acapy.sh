#!/bin/bash
set -e

cd /usr/src/app

poetry run aca-py start \
  --auto-provision \
  --inbound-transport http 0.0.0.0 8001 \
  --outbound-transport http \
  --endpoint http://acapy:8001 \
  --admin 0.0.0.0 8031 \
  --oauth-jwks-uri "${KEYCLOAK_REALM_URL}/protocol/openid-connect/certs" \
  --oauth-issuer "${ACAPY_OAUTH_ISSUER}" \
  --oauth-audience "${ACAPY_OAUTH_AUDIENCE}" \
  --multitenant \
  --multitenant-admin \
  --jwt-secret "${ACAPY_JWT_SECRET}" \
  --wallet-type askar \
  --wallet-name demo-base-wallet \
  --wallet-key "${ACAPY_WALLET_KEY}" \
  --wallet-storage-type postgres_storage \
  --wallet-storage-config "{\"url\":\"${POSTGRES_HOST}:${POSTGRES_PORT}\",\"max_connections\":5}" \
  --wallet-storage-creds "{\"account\":\"${POSTGRES_USER}\",\"password\":\"${POSTGRES_PASSWORD}\",\"admin_account\":\"${POSTGRES_USER}\",\"admin_password\":\"${POSTGRES_PASSWORD}\"}" \
  --no-ledger \
  --label "oauth-demo-agent" \
  --log-level "${ACAPY_LOG_LEVEL}"
