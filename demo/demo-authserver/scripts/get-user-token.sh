#!/bin/bash
# Authenticates a demo user via Keycloak using authorization code + PKCE
# (front-channel, public client — no client secret needed).
#
# On first run it will:
#   - Create a public OIDC client 'acapy-user-login' (auth code + PKCE)
#   - Create a test user with configurable credentials
#
# Subsequent runs skip creation and re-authenticate.
#
# Usage:
#   ./scripts/get-user-token.sh [username] [password]
#
# Requires: curl, jq, python3, openssl
set -euo pipefail

# ── config ────────────────────────────────────────────────────────────────────

if [[ -f "$(dirname "$0")/../.env" ]]; then
  set -o allexport
  source "$(dirname "$0")/../.env"
  set +o allexport
fi

KEYCLOAK_URL=${KEYCLOAK_URL:-http://localhost:8080}
KEYCLOAK_REALM=${KEYCLOAK_REALM:-acapy}
KEYCLOAK_ADMIN=${KEYCLOAK_ADMIN:-admin}
KEYCLOAK_ADMIN_PASSWORD=${KEYCLOAK_ADMIN_PASSWORD:-admin}
TENANT_CLIENT_ID=${TENANT_CLIENT_ID:-acapy-tenant-demo}
ACAPY_URL=${ACAPY_URL:-http://localhost:8031}

USER_LOGIN_CLIENT_ID="acapy-user-login"
TEST_USERNAME="${1:-demo-user}"
TEST_PASSWORD="${2:-demo-password}"
TOKEN_ENDPOINT="${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token"

CALLBACK_PORT=9999
REDIRECT_URI="http://localhost:${CALLBACK_PORT}/callback"

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

# ── wait ──────────────────────────────────────────────────────────────────────

wait_for "Keycloak" "${KEYCLOAK_URL}/health/ready"

# ── Keycloak admin token ──────────────────────────────────────────────────────

KC_ADMIN_TOKEN=$(curl -sf -X POST \
  "${KEYCLOAK_URL}/realms/master/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=admin-cli" \
  -d "username=${KEYCLOAK_ADMIN}" \
  -d "password=${KEYCLOAK_ADMIN_PASSWORD}" \
  | jq -r '.access_token')

ADMIN_H="Authorization: Bearer ${KC_ADMIN_TOKEN}"
REALM_URL="${KEYCLOAK_URL}/admin/realms/${KEYCLOAK_REALM}"

# ── read wallet_id from Keycloak (set by setup-tenant.sh) ────────────────────

KC_CLIENT_UUID=$(curl -sf \
  "${REALM_URL}/clients?clientId=${TENANT_CLIENT_ID}" \
  -H "${ADMIN_H}" | jq -r '.[0].id // empty')

WALLET_ID=$(curl -sf \
  "${REALM_URL}/clients/${KC_CLIENT_UUID}/protocol-mappers/models" \
  -H "${ADMIN_H}" \
  | jq -r '.[] | select(.name == "wallet-id") | .config["claim.value"] // empty')

if [[ -z "${WALLET_ID}" || "${WALLET_ID}" == "PLACEHOLDER_WALLET_ID" ]]; then
  echo "ERROR: wallet_id not set on '${TENANT_CLIENT_ID}'. Run ./scripts/setup-tenant.sh first." >&2
  exit 1
fi

echo "==> Using wallet_id: ${WALLET_ID}"

# ── create user-login client if it doesn't exist ─────────────────────────────

EXISTING=$(curl -sf \
  "${REALM_URL}/clients?clientId=${USER_LOGIN_CLIENT_ID}" \
  -H "${ADMIN_H}" | jq -r '.[0].id // empty')

if [[ -z "${EXISTING}" ]]; then
  echo "==> Creating client '${USER_LOGIN_CLIENT_ID}'..."
  curl -sf -X POST "${REALM_URL}/clients" \
    -H "${ADMIN_H}" \
    -H "Content-Type: application/json" \
    -d "{
      \"clientId\": \"${USER_LOGIN_CLIENT_ID}\",
      \"name\": \"ACA-Py User Login\",
      \"enabled\": true,
      \"publicClient\": true,
      \"standardFlowEnabled\": true,
      \"directAccessGrantsEnabled\": false,
      \"serviceAccountsEnabled\": false,
      \"protocol\": \"openid-connect\",
      \"redirectUris\": [\"http://localhost:${CALLBACK_PORT}/*\"],
      \"webOrigins\": [\"+\"],
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
    }"
  echo "    Client created."
else
  echo "==> Client '${USER_LOGIN_CLIENT_ID}' already exists."
fi

# ── create test user if they don't exist ─────────────────────────────────────

EXISTING_USER=$(curl -sf \
  "${REALM_URL}/users?username=${TEST_USERNAME}&exact=true" \
  -H "${ADMIN_H}" | jq -r '.[0].id // empty')

if [[ -z "${EXISTING_USER}" ]]; then
  echo "==> Creating user '${TEST_USERNAME}'..."
  curl -sf -X POST "${REALM_URL}/users" \
    -H "${ADMIN_H}" \
    -H "Content-Type: application/json" \
    -d "{
      \"username\": \"${TEST_USERNAME}\",
      \"email\": \"${TEST_USERNAME}@demo.local\",
      \"firstName\": \"Demo\",
      \"lastName\": \"User\",
      \"enabled\": true,
      \"emailVerified\": true,
      \"credentials\": [{
        \"type\": \"password\",
        \"value\": \"${TEST_PASSWORD}\",
        \"temporary\": false
      }]
    }"
  echo "    User created."
else
  echo "==> User '${TEST_USERNAME}' already exists."
fi

# ── PKCE ──────────────────────────────────────────────────────────────────────

CODE_VERIFIER=$(openssl rand -base64 48 | tr -d '/+=' | head -c 43)
CODE_CHALLENGE=$(printf '%s' "${CODE_VERIFIER}" \
  | openssl dgst -sha256 -binary \
  | base64 | tr -d '=' | tr '+/' '-_')

# ── build auth URL and prompt user ───────────────────────────────────────────

AUTH_URL="${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/auth"
AUTH_URL+="?client_id=${USER_LOGIN_CLIENT_ID}"
AUTH_URL+="&response_type=code"
AUTH_URL+="&redirect_uri=$(python3 -c "import urllib.parse; print(urllib.parse.quote('${REDIRECT_URI}', safe=''))")"
AUTH_URL+="&scope=acapy%3Atenant"
AUTH_URL+="&code_challenge=${CODE_CHALLENGE}"
AUTH_URL+="&code_challenge_method=S256"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " Open this URL in your browser to log in:"
echo ""
echo "  ${AUTH_URL}"
echo ""
echo " Credentials: ${TEST_USERNAME} / ${TEST_PASSWORD}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "==> Waiting for callback on ${REDIRECT_URI}..."

# ── local callback receiver ───────────────────────────────────────────────────

AUTH_CODE=$(CALLBACK_PORT=${CALLBACK_PORT} python3 -c "
import http.server, urllib.parse, threading, os, sys

port = int(os.environ['CALLBACK_PORT'])
result = []

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        code = params.get('code', [None])[0]
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(b'<html><body><h2>Authentication complete!</h2><p>You can close this tab.</p></body></html>')
        result.append(code or '')
        threading.Thread(target=self.server.shutdown, daemon=True).start()
    def log_message(self, *args): pass

server = http.server.HTTPServer(('localhost', port), Handler)
server.serve_forever()
print(result[0] if result else '')
")

if [[ -z "${AUTH_CODE}" ]]; then
  echo "ERROR: No authorization code received." >&2
  exit 1
fi

echo "==> Authorization code received. Exchanging for token..."

# ── token exchange ────────────────────────────────────────────────────────────

TOKEN_RESPONSE=$(curl -s -X POST "${TOKEN_ENDPOINT}" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "client_id=${USER_LOGIN_CLIENT_ID}" \
  -d "code=${AUTH_CODE}" \
  -d "redirect_uri=${REDIRECT_URI}" \
  -d "code_verifier=${CODE_VERIFIER}")

ACCESS_TOKEN=$(echo "${TOKEN_RESPONSE}" | jq -r '.access_token // empty')

if [[ -z "${ACCESS_TOKEN}" ]]; then
  echo "ERROR: Token exchange failed." >&2
  echo "       Response: ${TOKEN_RESPONSE}" >&2
  exit 1
fi

# ── output ────────────────────────────────────────────────────────────────────

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " User token for '${TEST_USERNAME}'"
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
