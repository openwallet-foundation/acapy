#!/bin/bash
# Gets a tenant access token from Keycloak using client credentials
# (confidential client, server-to-server). The client must have a wallet_id
# claim configured — run ./scripts/setup-tenant.sh first.
#
# Usage:
#   ./scripts/get-tenant-token.sh [client_id] [client_secret]
#
# Requires: curl, jq
set -euo pipefail

if [[ -f "$(dirname "$0")/../.env" ]]; then
  set -o allexport
  source "$(dirname "$0")/../.env"
  set +o allexport
fi

KEYCLOAK_URL=${KEYCLOAK_URL:-http://localhost:8080}
KEYCLOAK_REALM=${KEYCLOAK_REALM:-acapy}
ACAPY_URL=${ACAPY_URL:-http://localhost:8031}

CLIENT_ID="${1:-${TENANT_CLIENT_ID:-acapy-tenant-demo}}"
CLIENT_SECRET="${2:-${TENANT_CLIENT_SECRET:-tenant-secret}}"

TOKEN_ENDPOINT="${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token"

TOKEN_RESPONSE=$(curl -sf -X POST "${TOKEN_ENDPOINT}" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=${CLIENT_ID}" \
  -d "client_secret=${CLIENT_SECRET}")

ACCESS_TOKEN=$(echo "${TOKEN_RESPONSE}" | jq -r '.access_token')

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " Tenant token (${CLIENT_ID})"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo " Claims:"
echo "${ACCESS_TOKEN}" \
  | cut -d. -f2 \
  | tr '_-' '/+' \
  | awk '{l=length($0)%4; if(l==2) print $0"=="; else if(l==3) print $0"="; else print $0}' \
  | base64 -d 2>/dev/null \
  | jq '{sub, scope, wallet_id, aud, exp}'
echo ""
echo " Access token:"
echo "${ACCESS_TOKEN}"
echo ""
echo " Test against ACA-Py:"
echo "   curl -s -H \"Authorization: Bearer ${ACCESS_TOKEN}\" \\"
echo "        ${ACAPY_URL}/connections | jq ."
echo ""
