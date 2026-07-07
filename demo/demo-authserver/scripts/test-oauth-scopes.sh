#!/bin/bash
# Tests OAuth2 scope enforcement against the demo ACA-Py instance.
# Runs positive and negative test cases across all configured clients
# and writes a markdown report.
#
# Prerequisites: all services healthy, ./scripts/setup-tenant.sh already run.
#
# Usage:
#   ./scripts/test-oauth-scopes.sh
#
# Requires: curl, jq
set -euo pipefail

# ── config ────────────────────────────────────────────────────────────────────

if [[ -f "$(dirname "$0")/../.env" ]]; then
  set -o allexport
  source "$(dirname "$0")/../.env"
  set +o allexport
fi

KEYCLOAK_URL=${KEYCLOAK_URL:-http://localhost:8080}
KEYCLOAK_REALM=${KEYCLOAK_REALM:-acapy}
ACAPY_URL=${ACAPY_URL:-http://localhost:8031}
CONTROLLER_CLIENT_ID=${CONTROLLER_CLIENT_ID:-acapy-controller}
CONTROLLER_CLIENT_SECRET=${CONTROLLER_CLIENT_SECRET:-controller-secret}
TENANT_CLIENT_ID=${TENANT_CLIENT_ID:-acapy-tenant-demo}
TENANT_CLIENT_SECRET=${TENANT_CLIENT_SECRET:-tenant-secret}
READONLY_CLIENT_ID=${READONLY_CLIENT_ID:-acapy-tenant-readonly}
READONLY_CLIENT_SECRET=${READONLY_CLIENT_SECRET:-readonly-secret}
LIMITED_CLIENT_ID=${LIMITED_CLIENT_ID:-acapy-tenant-limited}
LIMITED_CLIENT_SECRET=${LIMITED_CLIENT_SECRET:-limited-secret}

TOKEN_ENDPOINT="${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token"
REPORT_FILE="$(dirname "$0")/../oauth-scope-test-report.md"

# ── colours ───────────────────────────────────────────────────────────────────

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

# ── state ─────────────────────────────────────────────────────────────────────

PASS=0
FAIL=0
REPORT_ROWS=()

# ── helpers ───────────────────────────────────────────────────────────────────

wait_for() {
  local label="$1" url="$2"
  echo -n "==> Waiting for ${label}..."
  until curl -sf "${url}" > /dev/null 2>&1; do printf "."; sleep 3; done
  echo " ready."
}

# Returns HTTP status code for a request.
# Usage: http_get <url> [token]
#        http_post <url> [token] [json_body]
http_get() {
  local url="$1" token="${2:-}"
  if [[ -n "$token" ]]; then
    curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $token" "$url"
  else
    curl -s -o /dev/null -w "%{http_code}" "$url"
  fi
}

http_post() {
  local url="$1" token="${2:-}" body="${3:-}"
  [[ -z "$body" ]] && body='{}'
  if [[ -n "$token" ]]; then
    curl -s -o /dev/null -w "%{http_code}" -X POST \
      -H "Authorization: Bearer $token" \
      -H "Content-Type: application/json" \
      -d "$body" "$url"
  else
    curl -s -o /dev/null -w "%{http_code}" -X POST \
      -H "Content-Type: application/json" \
      -d "$body" "$url"
  fi
}

http_post_form() {
  local url="$1" token="${2:-}"
  if [[ -n "$token" ]]; then
    curl -s -o /dev/null -w "%{http_code}" -X POST \
      -H "Authorization: Bearer $token" \
      -H "Content-Type: application/x-www-form-urlencoded" \
      "$url"
  else
    curl -s -o /dev/null -w "%{http_code}" -X POST \
      -H "Content-Type: application/x-www-form-urlencoded" \
      "$url"
  fi
}

# run_test <description> <expected_status> <actual_status> <group>
run_test() {
  local desc="$1" expected="$2" actual="$3" group="$4"
  local icon result

  if [[ "${actual}" == "${expected}" ]]; then
    icon="${GREEN}PASS${NC}"
    result="PASS"
    PASS=$((PASS + 1))
  else
    icon="${RED}FAIL${NC}"
    result="FAIL  ← got ${actual}"
    FAIL=$((FAIL + 1))
  fi

  printf "  [${icon}] %-60s expected=%s got=%s\n" "${desc}" "${expected}" "${actual}"
  REPORT_ROWS+=("| ${group} | ${desc} | ${expected} | ${actual} | ${result} |")
}

# ── wait for services ─────────────────────────────────────────────────────────

wait_for "Keycloak" "${KEYCLOAK_URL}/health/ready"
wait_for "ACA-Py"   "${ACAPY_URL}/status/ready"

# ── obtain tokens ─────────────────────────────────────────────────────────────

echo ""
echo "==> Obtaining tokens..."

ADMIN_TOKEN=$(curl -sf -X POST "${TOKEN_ENDPOINT}" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=${CONTROLLER_CLIENT_ID}" \
  -d "client_secret=${CONTROLLER_CLIENT_SECRET}" \
  | jq -r '.access_token')
echo "    admin token:  obtained (${CONTROLLER_CLIENT_ID})"

TENANT_TOKEN=$(curl -sf -X POST "${TOKEN_ENDPOINT}" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=${TENANT_CLIENT_ID}" \
  -d "client_secret=${TENANT_CLIENT_SECRET}" \
  | jq -r '.access_token')
echo "    tenant token: obtained (${TENANT_CLIENT_ID})"

# Verify wallet_id is set in the tenant token
WALLET_ID=$(echo "${TENANT_TOKEN}" \
  | cut -d. -f2 \
  | tr '_-' '/+' \
  | awk '{l=length($0)%4; if(l==2) print $0"=="; else if(l==3) print $0"="; else print $0}' \
  | base64 -d 2>/dev/null \
  | jq -r '.wallet_id // empty')

if [[ -z "${WALLET_ID}" || "${WALLET_ID}" == "PLACEHOLDER_WALLET_ID" ]]; then
  echo ""
  echo "ERROR: tenant token does not contain a valid wallet_id claim."
  echo "       Run ./scripts/setup-tenant.sh first."
  exit 1
fi
echo "    wallet_id:    ${WALLET_ID}"

READONLY_TOKEN=$(curl -sf -X POST "${TOKEN_ENDPOINT}" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=${READONLY_CLIENT_ID}" \
  -d "client_secret=${READONLY_CLIENT_SECRET}" \
  | jq -r '.access_token')
echo "    readonly token: obtained (${READONLY_CLIENT_ID})"

LIMITED_TOKEN=$(curl -sf -X POST "${TOKEN_ENDPOINT}" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=${LIMITED_CLIENT_ID}" \
  -d "client_secret=${LIMITED_CLIENT_SECRET}" \
  | jq -r '.access_token')
echo "    limited token:  obtained (${LIMITED_CLIENT_ID})"

# Create a temporary wallet for admin write tests, then remove it
TEST_WALLET_NAME="oauth-scope-test-$$"
echo "    Creating temporary test wallet '${TEST_WALLET_NAME}'..."
CREATE_RESP=$(curl -s -X POST "${ACAPY_URL}/multitenancy/wallet" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"label\":\"${TEST_WALLET_NAME}\",\"wallet_name\":\"${TEST_WALLET_NAME}\",\"wallet_type\":\"askar\",\"wallet_key\":\"${TEST_WALLET_NAME}-key\",\"key_management_mode\":\"managed\"}")
TEST_WALLET_ID=$(echo "${CREATE_RESP}" | jq -r '.wallet_id // empty')
if [[ -z "${TEST_WALLET_ID}" ]]; then
  echo "WARNING: Could not create temporary test wallet. Skipping wallet-create/delete tests."
fi

# ── run tests ─────────────────────────────────────────────────────────────────

echo ""
printf "${BOLD}%-70s %-10s %-10s\n${NC}" "Test" "Expected" "Actual"
printf '%0.s─' {1..95}; echo ""

# ── Group 1: Public endpoints (no token required) ─────────────────────────────

echo ""
printf "${YELLOW}Group 1: Public endpoints (no authentication)${NC}\n"

run_test "GET /status/ready — no token"       "200" "$(http_get "${ACAPY_URL}/status/ready")"               "Public"
run_test "GET /status/live  — no token"       "200" "$(http_get "${ACAPY_URL}/status/live")"                "Public"

# ── Group 2: Unauthenticated requests to protected endpoints ──────────────────

echo ""
printf "${YELLOW}Group 2: Protected endpoints — no token (expect 401)${NC}\n"

run_test "GET /multitenancy/wallets — no token"   "401" "$(http_get "${ACAPY_URL}/multitenancy/wallets")"  "No token"
run_test "GET /connections — no token"            "401" "$(http_get "${ACAPY_URL}/connections")"           "No token"
run_test "GET /credentials — no token"            "401" "$(http_get "${ACAPY_URL}/credentials")"           "No token"

# ── Group 3: Invalid token ────────────────────────────────────────────────────

echo ""
printf "${YELLOW}Group 3: Invalid bearer token (expect 401)${NC}\n"

run_test "GET /multitenancy/wallets — invalid token" "401" "$(http_get "${ACAPY_URL}/multitenancy/wallets" "not-a-valid-token")" "Invalid token"
run_test "GET /connections — invalid token"          "401" "$(http_get "${ACAPY_URL}/connections" "not-a-valid-token")"          "Invalid token"

# ── Group 4: Admin token — GET (acapy:admin scope) ───────────────────────────

echo ""
printf "${YELLOW}Group 4: Admin token — GET routes (acapy:admin scope)${NC}\n"

run_test "GET /status/ready — admin token"              "200" "$(http_get "${ACAPY_URL}/status/ready" "${ADMIN_TOKEN}")"            "Admin GET"
run_test "GET /status/config — admin token"             "200" "$(http_get "${ACAPY_URL}/status/config" "${ADMIN_TOKEN}")"           "Admin GET"
run_test "GET /multitenancy/wallets — admin token"      "200" "$(http_get "${ACAPY_URL}/multitenancy/wallets" "${ADMIN_TOKEN}")"    "Admin GET"
run_test "GET /connections — admin token"               "200" "$(http_get "${ACAPY_URL}/connections" "${ADMIN_TOKEN}")"             "Admin GET"
run_test "GET /credentials — admin token"               "200" "$(http_get "${ACAPY_URL}/credentials" "${ADMIN_TOKEN}")"             "Admin GET"

if [[ -n "${TEST_WALLET_ID}" ]]; then
  run_test "GET /multitenancy/wallet/{id} — admin token" "200" \
    "$(http_get "${ACAPY_URL}/multitenancy/wallet/${TEST_WALLET_ID}" "${ADMIN_TOKEN}")" \
    "Admin GET"
fi

# ── Group 5: Admin token — POST (acapy:admin scope) ──────────────────────────

echo ""
printf "${YELLOW}Group 5: Admin token — POST routes (acapy:admin scope)${NC}\n"

run_test "POST /wallet/did/create — admin token" "200" \
  "$(http_post "${ACAPY_URL}/wallet/did/create" "${ADMIN_TOKEN}" '{"method":"key","options":{"key_type":"ed25519"}}')" \
  "Admin POST"

if [[ -n "${TEST_WALLET_ID}" ]]; then
  run_test "POST /multitenancy/wallet/{id}/remove — admin token" "200" \
    "$(http_post_form "${ACAPY_URL}/multitenancy/wallet/${TEST_WALLET_ID}/remove" "${ADMIN_TOKEN}")" \
    "Admin POST"
fi

# ── Group 6: Tenant token — GET (acapy:tenant scope) ─────────────────────────

echo ""
printf "${YELLOW}Group 6: Tenant token — GET routes (acapy:tenant scope)${NC}\n"

run_test "GET /connections — tenant token"              "200" "$(http_get "${ACAPY_URL}/connections" "${TENANT_TOKEN}")"            "Tenant GET"
run_test "GET /credentials — tenant token"              "200" "$(http_get "${ACAPY_URL}/credentials" "${TENANT_TOKEN}")"            "Tenant GET"
run_test "GET /wallet/did — tenant token"               "200" "$(http_get "${ACAPY_URL}/wallet/did" "${TENANT_TOKEN}")"            "Tenant GET"

# ── Group 7: Tenant token — POST (acapy:tenant scope) ────────────────────────

echo ""
printf "${YELLOW}Group 7: Tenant token — POST routes (acapy:tenant scope)${NC}\n"

run_test "POST /wallet/did/create — tenant token" "200" \
  "$(http_post "${ACAPY_URL}/wallet/did/create" "${TENANT_TOKEN}" '{"method":"key","options":{"key_type":"ed25519"}}')" \
  "Tenant POST"

# ── Group 8: Tenant token — admin endpoints (expect 403) ─────────────────────

echo ""
printf "${YELLOW}Group 8: Tenant token — admin endpoints (expect 403 Forbidden)${NC}\n"

run_test "GET /multitenancy/wallets — tenant token"     "403" "$(http_get "${ACAPY_URL}/multitenancy/wallets" "${TENANT_TOKEN}")"  "Tenant→Admin"
run_test "GET /multitenancy/wallet/{id} — tenant token" "403" \
  "$(http_get "${ACAPY_URL}/multitenancy/wallet/${WALLET_ID}" "${TENANT_TOKEN}")" \
  "Tenant→Admin"
run_test "GET /status/config — tenant token"            "403" "$(http_get "${ACAPY_URL}/status/config" "${TENANT_TOKEN}")"         "Tenant→Admin"

# ── Group 9: Read-only tenant token (acapy:tenant:read) ──────────────────────

echo ""
printf "${YELLOW}Group 9: Read-only token — acapy:tenant:read scope${NC}\n"

run_test "GET /connections — readonly token"             "200" "$(http_get "${ACAPY_URL}/connections" "${READONLY_TOKEN}")"          "Read-only"
run_test "GET /credentials — readonly token"             "200" "$(http_get "${ACAPY_URL}/credentials" "${READONLY_TOKEN}")"          "Read-only"
run_test "GET /wallet/did — readonly token"              "200" "$(http_get "${ACAPY_URL}/wallet/did" "${READONLY_TOKEN}")"           "Read-only"
run_test "POST /wallet/did/create — readonly token" "403" \
  "$(http_post "${ACAPY_URL}/wallet/did/create" "${READONLY_TOKEN}" '{"method":"key","options":{"key_type":"ed25519"}}')" \
  "Read-only"
run_test "GET /multitenancy/wallets — readonly token"    "403" "$(http_get "${ACAPY_URL}/multitenancy/wallets" "${READONLY_TOKEN}")" "Read-only"

# ── Group 10: acapy:wallet:create scope enforcement ──────────────────────────
# limited token has acapy:tenant but NOT acapy:wallet:create.
# Demonstrates require_scope blocking POST /wallet/did/create even though
# tenant_authentication passes (acapy:tenant is present).

echo ""
printf "${YELLOW}Group 10: acapy:wallet:create scope enforcement${NC}\n"

run_test "GET /connections — limited token (acapy:tenant, no wallet:create)"    "200" \
  "$(http_get "${ACAPY_URL}/connections" "${LIMITED_TOKEN}")" \
  "wallet:create scope"

run_test "POST /wallet/did/create — limited token (missing acapy:wallet:create)" "403" \
  "$(http_post "${ACAPY_URL}/wallet/did/create" "${LIMITED_TOKEN}" '{"method":"key","options":{"key_type":"ed25519"}}')" \
  "wallet:create scope"

run_test "POST /wallet/did/create — tenant token (has acapy:wallet:create)"      "200" \
  "$(http_post "${ACAPY_URL}/wallet/did/create" "${TENANT_TOKEN}" '{"method":"key","options":{"key_type":"ed25519"}}')" \
  "wallet:create scope"

run_test "POST /wallet/did/create — admin token (acapy:admin satisfies require_scope)" "200" \
  "$(http_post "${ACAPY_URL}/wallet/did/create" "${ADMIN_TOKEN}" '{"method":"key","options":{"key_type":"ed25519"}}')" \
  "wallet:create scope"

# ── summary ───────────────────────────────────────────────────────────────────

TOTAL=$((PASS + FAIL))
echo ""
printf '%0.s─' {1..95}; echo ""
printf "${BOLD}Results: ${GREEN}${PASS} passed${NC}${BOLD}, ${RED}${FAIL} failed${NC}${BOLD}, ${TOTAL} total${NC}\n"

# ── write markdown report ─────────────────────────────────────────────────────

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

{
  echo "# OAuth Scope Test Report"
  echo ""
  echo "**Date:** ${TIMESTAMP}"
  echo "**ACA-Py:** ${ACAPY_URL}"
  echo "**Keycloak realm:** ${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}"
  echo "**Wallet ID under test:** ${WALLET_ID}"
  echo ""
  echo "## Summary"
  echo ""
  echo "| Result | Count |"
  echo "|--------|-------|"
  echo "| Passed | ${PASS} |"
  echo "| Failed | ${FAIL} |"
  echo "| Total  | ${TOTAL} |"
  echo ""
  echo "## Test Cases"
  echo ""
  echo "| Group | Test | Expected | Actual | Result |"
  echo "|-------|------|----------|--------|--------|"
  for row in "${REPORT_ROWS[@]}"; do
    echo "${row}"
  done
  echo ""
  echo "## Scope Matrix"
  echo ""
  echo "| Endpoint | No token | Invalid token | acapy:admin | acapy:tenant + acapy:wallet:create | acapy:tenant (no wallet:create) | acapy:tenant:read |"
  echo "|----------|----------|---------------|-------------|-------------------------------------|----------------------------------|-------------------|"
  echo "| \`GET /status/ready\` | 200 | 200 | 200 | 200 | 200 | 200 |"
  echo "| \`GET /status/config\` | 401 | 401 | 200 | 403 | 403 | 403 |"
  echo "| \`GET /multitenancy/wallets\` | 401 | 401 | 200 | 403 | 403 | 403 |"
  echo "| \`GET /multitenancy/wallet/{id}\` | 401 | 401 | 200 | 403 | 403 | 403 |"
  echo "| \`GET /connections\` | 401 | 401 | 200 | 200 | 200 | 200 |"
  echo "| \`GET /credentials\` | 401 | 401 | 200 | 200 | 200 | 200 |"
  echo "| \`GET /wallet/did\` | 401 | 401 | 200 | 200 | 200 | 200 |"
  echo "| \`POST /wallet/did/create\` | 401 | 401 | 200 | 200 | **403** | 403 |"
  echo "| \`POST /multitenancy/wallet/{id}/remove\` | 401 | 401 | 200 | 403 | 403 | 403 |"
} > "${REPORT_FILE}"

echo ""
echo "==> Report written to: ${REPORT_FILE}"
echo ""

[[ ${FAIL} -gt 0 ]] && exit 1 || exit 0
