#!/bin/bash
# Gets an admin access token from Keycloak using client credentials
# (acapy-controller service account, acapy:admin scope).
#
# Usage:
#   ./scripts/get-admin-token.sh
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
CONTROLLER_CLIENT_ID=${CONTROLLER_CLIENT_ID:-acapy-controller}
CONTROLLER_CLIENT_SECRET=${CONTROLLER_CLIENT_SECRET:-controller-secret}
ACAPY_URL=${ACAPY_URL:-http://localhost:8031}

TOKEN_ENDPOINT="${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token"

TOKEN_RESPONSE=$(curl -sf -X POST "${TOKEN_ENDPOINT}" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=${CONTROLLER_CLIENT_ID}" \
  -d "client_secret=${CONTROLLER_CLIENT_SECRET}")

ACCESS_TOKEN=$(echo "${TOKEN_RESPONSE}" | jq -r '.access_token')

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " Admin token (${CONTROLLER_CLIENT_ID})"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo " Claims:"
echo "${ACCESS_TOKEN}" \
  | cut -d. -f2 \
  | tr '_-' '/+' \
  | awk '{l=length($0)%4; if(l==2) print $0"=="; else if(l==3) print $0"="; else print $0}' \
  | base64 -d 2>/dev/null \
  | jq '{sub, scope, aud, exp}'
echo ""
echo " Access token:"
echo "${ACCESS_TOKEN}"
echo ""
echo " Test against ACA-Py:"
echo "   curl -s -H \"Authorization: Bearer ${ACCESS_TOKEN}\" \\"
echo "        ${ACAPY_URL}/multitenancy/wallets | jq ."
echo ""
