#!/bin/bash
# Provisions a demo tenant wallet in ACA-Py and wires the wallet_id
# back into the Keycloak acapy-tenant-demo client as a hardcoded claim.
#
# Run this from the host after all services are healthy:
#   ./scripts/setup-tenant.sh
#
# Requires: curl, jq
set -euo pipefail

# Load .env if present and not already set
if [[ -f "$(dirname "$0")/../.env" ]]; then
  set -o allexport
  source "$(dirname "$0")/../.env"
  set +o allexport
fi

KEYCLOAK_URL=${KEYCLOAK_URL:-http://localhost:8080}
KEYCLOAK_REALM=${KEYCLOAK_REALM:-acapy}
KEYCLOAK_ADMIN=${KEYCLOAK_ADMIN:-admin}
KEYCLOAK_ADMIN_PASSWORD=${KEYCLOAK_ADMIN_PASSWORD:-admin}
ACAPY_URL=${ACAPY_URL:-http://localhost:8031}
CONTROLLER_CLIENT_ID=${CONTROLLER_CLIENT_ID:-acapy-controller}
CONTROLLER_CLIENT_SECRET=${CONTROLLER_CLIENT_SECRET:-controller-secret}
TENANT_CLIENT_ID=${TENANT_CLIENT_ID:-acapy-tenant-demo}
READONLY_CLIENT_ID=${READONLY_CLIENT_ID:-acapy-tenant-readonly}
READONLY_CLIENT_SECRET=${READONLY_CLIENT_SECRET:-readonly-secret}
LIMITED_CLIENT_ID=${LIMITED_CLIENT_ID:-acapy-tenant-limited}
LIMITED_CLIENT_SECRET=${LIMITED_CLIENT_SECRET:-limited-secret}
WALLET_NAME=${WALLET_NAME:-demo-tenant}
REALM_URL="${KEYCLOAK_URL}/admin/realms/${KEYCLOAK_REALM}"

# ── helpers ───────────────────────────────────────────────────────────────────

wait_for() {
  local label="$1" url="$2"
  echo -n "==> Waiting for ${label}..."
  until curl -sf "${url}" > /dev/null 2>&1; do
    echo -n "."
    sleep 3
  done
  echo " ready."
}

# ── wait for services ─────────────────────────────────────────────────────────

wait_for "Keycloak" "${KEYCLOAK_URL}/health/ready"
wait_for "ACA-Py"   "${ACAPY_URL}/status/ready"

# ── Keycloak admin token (master realm) ───────────────────────────────────────

echo "==> Authenticating with Keycloak admin..."
KC_ADMIN_TOKEN=$(curl -sf -X POST \
  "${KEYCLOAK_URL}/realms/master/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=admin-cli" \
  -d "username=${KEYCLOAK_ADMIN}" \
  -d "password=${KEYCLOAK_ADMIN_PASSWORD}" \
  | jq -r '.access_token')

# ── ACA-Py admin token (controller client credentials) ────────────────────────

echo "==> Getting ACA-Py admin access token..."
ACAPY_TOKEN=$(curl -sf -X POST \
  "${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=${CONTROLLER_CLIENT_ID}" \
  -d "client_secret=${CONTROLLER_CLIENT_SECRET}" \
  | jq -r '.access_token')

# ── create sub-wallet ─────────────────────────────────────────────────────────

echo "==> Creating sub-wallet '${WALLET_NAME}'..."
WALLET_RESPONSE=$(curl -s -X POST \
  "${ACAPY_URL}/multitenancy/wallet" \
  -H "Authorization: Bearer ${ACAPY_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"label\": \"${WALLET_NAME}\",
    \"wallet_name\": \"${WALLET_NAME}\",
    \"wallet_type\": \"askar\",
    \"wallet_key\": \"${WALLET_NAME}-key\",
    \"key_management_mode\": \"managed\"
  }")
WALLET_ID=$(echo "${WALLET_RESPONSE}" | jq -r '.wallet_id // empty' 2>/dev/null || true)

if [[ -z "${WALLET_ID}" ]]; then
  echo "    Create response: ${WALLET_RESPONSE}"
  echo "    Querying for existing wallet..."
  QUERY_RESPONSE=$(curl -s \
    "${ACAPY_URL}/multitenancy/wallets?wallet_name=${WALLET_NAME}" \
    -H "Authorization: Bearer ${ACAPY_TOKEN}")
  echo "    Query response: ${QUERY_RESPONSE}"
  WALLET_ID=$(echo "${QUERY_RESPONSE}" | jq -r '.results[0].wallet_id // empty' 2>/dev/null || true)
fi

if [[ -z "${WALLET_ID}" ]]; then
  echo "ERROR: Could not create or find wallet '${WALLET_NAME}'." >&2
  exit 1
fi
echo "    wallet_id: ${WALLET_ID}"

# ── update Keycloak wallet_id claim ──────────────────────────────────────────

echo "==> Updating Keycloak wallet-id claim for client '${TENANT_CLIENT_ID}'..."

KC_CLIENT_UUID=$(curl -sf \
  "${REALM_URL}/clients?clientId=${TENANT_CLIENT_ID}" \
  -H "Authorization: Bearer ${KC_ADMIN_TOKEN}" \
  | jq -r '.[0].id // empty')

if [[ -z "${KC_CLIENT_UUID}" ]]; then
  echo "ERROR: Client '${TENANT_CLIENT_ID}' not found in Keycloak realm '${KEYCLOAK_REALM}'." >&2
  exit 1
fi
echo "    client UUID: ${KC_CLIENT_UUID}"

# Remove any existing wallet-id mapper (handles both import-created and
# previously set by this script).  Ignore 404 — mapper may not exist yet.
MAPPER_ID=$(curl -sf \
  "${REALM_URL}/clients/${KC_CLIENT_UUID}/protocol-mappers/models" \
  -H "Authorization: Bearer ${KC_ADMIN_TOKEN}" \
  | jq -r '.[] | select(.name == "wallet-id") | .id // empty')

if [[ -n "${MAPPER_ID}" ]]; then
  echo "    Removing existing wallet-id mapper (${MAPPER_ID})..."
  curl -sf -X DELETE \
    "${REALM_URL}/clients/${KC_CLIENT_UUID}/protocol-mappers/models/${MAPPER_ID}" \
    -H "Authorization: Bearer ${KC_ADMIN_TOKEN}"
fi

# Create a fresh mapper with the correct wallet_id value
echo "    Creating wallet-id mapper..."
CREATE_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
  "${REALM_URL}/clients/${KC_CLIENT_UUID}/protocol-mappers/models" \
  -H "Authorization: Bearer ${KC_ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"wallet-id\",
    \"protocol\": \"openid-connect\",
    \"protocolMapper\": \"oidc-hardcoded-claim-mapper\",
    \"consentRequired\": false,
    \"config\": {
      \"claim.name\": \"wallet_id\",
      \"claim.value\": \"${WALLET_ID}\",
      \"jsonType.label\": \"String\",
      \"id.token.claim\": \"false\",
      \"access.token.claim\": \"true\",
      \"userinfo.token.claim\": \"false\"
    }
  }")
if [[ "${CREATE_STATUS}" != "201" ]]; then
  echo "ERROR: Failed to create wallet-id mapper (HTTP ${CREATE_STATUS})." >&2
  exit 1
fi
echo "    Mapper created (HTTP ${CREATE_STATUS})."

# Verify — fetch mapper list and confirm wallet_id value is set correctly
ACTUAL_WALLET_ID=$(curl -sf \
  "${REALM_URL}/clients/${KC_CLIENT_UUID}/protocol-mappers/models" \
  -H "Authorization: Bearer ${KC_ADMIN_TOKEN}" \
  | jq -r '.[] | select(.name == "wallet-id") | .config["claim.value"] // empty')
echo "    Verified claim.value in Keycloak: ${ACTUAL_WALLET_ID}"
if [[ "${ACTUAL_WALLET_ID}" != "${WALLET_ID}" ]]; then
  echo "ERROR: Keycloak mapper value does not match wallet_id (${ACTUAL_WALLET_ID} != ${WALLET_ID})." >&2
  exit 1
fi

# ── provision read-only tenant Keycloak client ───────────────────────────────

echo "==> Provisioning read-only tenant client '${READONLY_CLIENT_ID}'..."

READONLY_CLIENT_UUID=$(curl -sf \
  "${REALM_URL}/clients?clientId=${READONLY_CLIENT_ID}" \
  -H "Authorization: Bearer ${KC_ADMIN_TOKEN}" \
  | jq -r '.[0].id // empty')

if [[ -z "${READONLY_CLIENT_UUID}" ]]; then
  echo "    Creating client..."
  curl -sf -X POST "${REALM_URL}/clients" \
    -H "Authorization: Bearer ${KC_ADMIN_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{
      \"clientId\": \"${READONLY_CLIENT_ID}\",
      \"enabled\": true,
      \"publicClient\": false,
      \"serviceAccountsEnabled\": true,
      \"standardFlowEnabled\": false,
      \"clientAuthenticatorType\": \"client-secret\",
      \"secret\": \"${READONLY_CLIENT_SECRET}\",
      \"defaultClientScopes\": [\"acapy:tenant:read\"],
      \"optionalClientScopes\": [],
      \"protocolMappers\": [
        {
          \"name\": \"audience-acapy\",
          \"protocol\": \"openid-connect\",
          \"protocolMapper\": \"oidc-audience-mapper\",
          \"consentRequired\": false,
          \"config\": {
            \"included.client.audience\": \"acapy-resource-server\",
            \"id.token.claim\": \"false\",
            \"access.token.claim\": \"true\"
          }
        },
        {
          \"name\": \"wallet-id\",
          \"protocol\": \"openid-connect\",
          \"protocolMapper\": \"oidc-hardcoded-claim-mapper\",
          \"consentRequired\": false,
          \"config\": {
            \"claim.name\": \"wallet_id\",
            \"claim.value\": \"${WALLET_ID}\",
            \"jsonType.label\": \"String\",
            \"id.token.claim\": \"false\",
            \"access.token.claim\": \"true\",
            \"userinfo.token.claim\": \"false\"
          }
        }
      ]
    }" > /dev/null
  READONLY_CLIENT_UUID=$(curl -sf \
    "${REALM_URL}/clients?clientId=${READONLY_CLIENT_ID}" \
    -H "Authorization: Bearer ${KC_ADMIN_TOKEN}" \
    | jq -r '.[0].id // empty')
  echo "    Client created (UUID: ${READONLY_CLIENT_UUID})."
else
  echo "    Client exists (UUID: ${READONLY_CLIENT_UUID}), updating wallet-id mapper..."
  RO_MAPPER_ID=$(curl -sf \
    "${REALM_URL}/clients/${READONLY_CLIENT_UUID}/protocol-mappers/models" \
    -H "Authorization: Bearer ${KC_ADMIN_TOKEN}" \
    | jq -r '.[] | select(.name == "wallet-id") | .id // empty')
  if [[ -n "${RO_MAPPER_ID}" ]]; then
    curl -sf -X DELETE \
      "${REALM_URL}/clients/${READONLY_CLIENT_UUID}/protocol-mappers/models/${RO_MAPPER_ID}" \
      -H "Authorization: Bearer ${KC_ADMIN_TOKEN}"
  fi
  curl -sf -X POST \
    "${REALM_URL}/clients/${READONLY_CLIENT_UUID}/protocol-mappers/models" \
    -H "Authorization: Bearer ${KC_ADMIN_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{
      \"name\": \"wallet-id\",
      \"protocol\": \"openid-connect\",
      \"protocolMapper\": \"oidc-hardcoded-claim-mapper\",
      \"consentRequired\": false,
      \"config\": {
        \"claim.name\": \"wallet_id\",
        \"claim.value\": \"${WALLET_ID}\",
        \"jsonType.label\": \"String\",
        \"id.token.claim\": \"false\",
        \"access.token.claim\": \"true\",
        \"userinfo.token.claim\": \"false\"
      }
    }" > /dev/null
  echo "    wallet-id mapper updated."
fi

# ── assign acapy:wallet:create scope to tenant demo client ───────────────────

echo "==> Assigning acapy:wallet:create scope to client '${TENANT_CLIENT_ID}'..."

# Look up the UUID of the acapy:wallet:create client scope
WALLET_CREATE_SCOPE_UUID=$(curl -sf \
  "${REALM_URL}/client-scopes" \
  -H "Authorization: Bearer ${KC_ADMIN_TOKEN}" \
  | jq -r '.[] | select(.name == "acapy:wallet:create") | .id // empty')

if [[ -z "${WALLET_CREATE_SCOPE_UUID}" ]]; then
  echo "ERROR: 'acapy:wallet:create' client scope not found in realm '${KEYCLOAK_REALM}'." >&2
  echo "       Ensure the realm was imported from keycloak/realm-export.json." >&2
  exit 1
fi
echo "    acapy:wallet:create scope UUID: ${WALLET_CREATE_SCOPE_UUID}"

# Assign as a default scope on the tenant demo client (idempotent — 409 is fine)
ASSIGN_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X PUT \
  "${REALM_URL}/clients/${KC_CLIENT_UUID}/default-client-scopes/${WALLET_CREATE_SCOPE_UUID}" \
  -H "Authorization: Bearer ${KC_ADMIN_TOKEN}")
if [[ "${ASSIGN_STATUS}" == "204" || "${ASSIGN_STATUS}" == "409" ]]; then
  echo "    acapy:wallet:create scope assigned (HTTP ${ASSIGN_STATUS})."
else
  echo "ERROR: Failed to assign acapy:wallet:create scope (HTTP ${ASSIGN_STATUS})." >&2
  exit 1
fi

# ── provision limited tenant Keycloak client ─────────────────────────────────

echo "==> Provisioning limited tenant client '${LIMITED_CLIENT_ID}'..."

LIMITED_CLIENT_UUID=$(curl -sf \
  "${REALM_URL}/clients?clientId=${LIMITED_CLIENT_ID}" \
  -H "Authorization: Bearer ${KC_ADMIN_TOKEN}" \
  | jq -r '.[0].id // empty')

if [[ -z "${LIMITED_CLIENT_UUID}" ]]; then
  echo "    Creating client..."
  curl -sf -X POST "${REALM_URL}/clients" \
    -H "Authorization: Bearer ${KC_ADMIN_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{
      \"clientId\": \"${LIMITED_CLIENT_ID}\",
      \"enabled\": true,
      \"publicClient\": false,
      \"serviceAccountsEnabled\": true,
      \"standardFlowEnabled\": false,
      \"clientAuthenticatorType\": \"client-secret\",
      \"secret\": \"${LIMITED_CLIENT_SECRET}\",
      \"defaultClientScopes\": [\"acapy:tenant\"],
      \"optionalClientScopes\": [],
      \"protocolMappers\": [
        {
          \"name\": \"audience-acapy\",
          \"protocol\": \"openid-connect\",
          \"protocolMapper\": \"oidc-audience-mapper\",
          \"consentRequired\": false,
          \"config\": {
            \"included.client.audience\": \"acapy-resource-server\",
            \"id.token.claim\": \"false\",
            \"access.token.claim\": \"true\"
          }
        },
        {
          \"name\": \"wallet-id\",
          \"protocol\": \"openid-connect\",
          \"protocolMapper\": \"oidc-hardcoded-claim-mapper\",
          \"consentRequired\": false,
          \"config\": {
            \"claim.name\": \"wallet_id\",
            \"claim.value\": \"${WALLET_ID}\",
            \"jsonType.label\": \"String\",
            \"id.token.claim\": \"false\",
            \"access.token.claim\": \"true\",
            \"userinfo.token.claim\": \"false\"
          }
        }
      ]
    }" > /dev/null
  LIMITED_CLIENT_UUID=$(curl -sf \
    "${REALM_URL}/clients?clientId=${LIMITED_CLIENT_ID}" \
    -H "Authorization: Bearer ${KC_ADMIN_TOKEN}" \
    | jq -r '.[0].id // empty')
  echo "    Client created (UUID: ${LIMITED_CLIENT_UUID})."
else
  echo "    Client exists (UUID: ${LIMITED_CLIENT_UUID}), updating wallet-id mapper..."
  LIM_MAPPER_ID=$(curl -sf \
    "${REALM_URL}/clients/${LIMITED_CLIENT_UUID}/protocol-mappers/models" \
    -H "Authorization: Bearer ${KC_ADMIN_TOKEN}" \
    | jq -r '.[] | select(.name == "wallet-id") | .id // empty')
  if [[ -n "${LIM_MAPPER_ID}" ]]; then
    curl -sf -X DELETE \
      "${REALM_URL}/clients/${LIMITED_CLIENT_UUID}/protocol-mappers/models/${LIM_MAPPER_ID}" \
      -H "Authorization: Bearer ${KC_ADMIN_TOKEN}"
  fi
  curl -sf -X POST \
    "${REALM_URL}/clients/${LIMITED_CLIENT_UUID}/protocol-mappers/models" \
    -H "Authorization: Bearer ${KC_ADMIN_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{
      \"name\": \"wallet-id\",
      \"protocol\": \"openid-connect\",
      \"protocolMapper\": \"oidc-hardcoded-claim-mapper\",
      \"consentRequired\": false,
      \"config\": {
        \"claim.name\": \"wallet_id\",
        \"claim.value\": \"${WALLET_ID}\",
        \"jsonType.label\": \"String\",
        \"id.token.claim\": \"false\",
        \"access.token.claim\": \"true\",
        \"userinfo.token.claim\": \"false\"
      }
    }" > /dev/null
  echo "    wallet-id mapper updated."
fi

# ── summary ───────────────────────────────────────────────────────────────────

TOKEN_ENDPOINT="${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " Setup complete"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo " Wallet ID        : ${WALLET_ID}"
echo " Tenant client    : ${TENANT_CLIENT_ID}  (acapy:tenant + acapy:wallet:create)"
echo " Limited client   : ${LIMITED_CLIENT_ID}  (acapy:tenant only — no wallet:create)"
echo " Readonly client  : ${READONLY_CLIENT_ID}  (acapy:tenant:read only)"
echo " Admin API    : ${ACAPY_URL}/api/doc"
echo ""
echo " Get an admin token (acapy:admin scope):"
echo "   curl -s -X POST '${TOKEN_ENDPOINT}' \\"
echo "     -d 'grant_type=client_credentials' \\"
echo "     -d 'client_id=${CONTROLLER_CLIENT_ID}' \\"
echo "     -d 'client_secret=${CONTROLLER_CLIENT_SECRET}' \\"
echo "     | jq -r .access_token"
echo ""
echo " Get a tenant token (acapy:tenant scope + wallet_id=${WALLET_ID}):"
echo "   curl -s -X POST '${TOKEN_ENDPOINT}' \\"
echo "     -d 'grant_type=client_credentials' \\"
echo "     -d 'client_id=${TENANT_CLIENT_ID}' \\"
echo "     -d 'client_secret=${TENANT_CLIENT_SECRET:-tenant-secret}' \\"
echo "     | jq -r .access_token"
echo ""
echo " Call ACA-Py with the token:"
echo "   TOKEN=\$(curl -s ... | jq -r .access_token)"
echo "   curl -H \"Authorization: Bearer \$TOKEN\" ${ACAPY_URL}/connections"
echo ""
