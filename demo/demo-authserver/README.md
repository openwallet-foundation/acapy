# ACA-Py OAuth2 Resource Server Demo

This demo runs ACA-Py as an OAuth2 Resource Server backed by Keycloak as the Authorization Server. Access tokens are issued by Keycloak and presented to ACA-Py — no ACA-Py API key or ACA-Py-issued JWT is involved.

> This directory is the human-facing walkthrough. For the automated regression test that runs in CI, see [`scenarios/examples/oauth_resource_server`](../../scenarios/examples/oauth_resource_server). The two share the same Keycloak realm export — keep them in sync when changing client or scope configuration.

## Services

| Service | Port | Purpose |
|---|---|---|
| `keycloak` | 8080 | Authorization Server (Keycloak 24, dev mode) |
| `wallet-db` | — (internal) | PostgreSQL for ACA-Py wallet storage |
| `acapy` | 8031 (admin), 8001 (agent) | ACA-Py configured as OAuth2 Resource Server |

## Prerequisites

- Docker with Compose v2
- `curl` and `jq` (for the setup script)

## Keycloak Realm

The `keycloak/realm-export.json` file is imported automatically on first start. It configures:

**Client Scopes**

| Scope | Purpose |
|---|---|
| `acapy:admin` | Full administrative access |
| `acapy:tenant` | Tenant-level access (credentials, connections, presentations) |
| `acapy:tenant:read` | Read-only tenant access |
| `acapy:wallet:create` | Permission to create sub-wallets |

**Clients**

| Client ID | Grant | Default Scope | Purpose |
|---|---|---|---|
| `acapy-resource-server` | bearer-only | — | Registered RS; tokens include it in `aud` |
| `acapy-controller` | client_credentials | `acapy:admin` | Admin controller secret: `controller-secret` |
| `acapy-tenant-demo` | client_credentials | `acapy:tenant` | Demo tenant secret: `tenant-secret` |

The `acapy-tenant-demo` client includes a `wallet_id` hardcoded claim (initially set to `PLACEHOLDER_WALLET_ID`). The setup script replaces this with a real wallet UUID after provisioning.

## Quick Start

**Step 1 — Start all services**

```bash
cd demo/demo-authserver
docker compose up --build
```

Wait until all three services report healthy. This typically takes 60–90 seconds on first run while Keycloak initialises.

**Step 2 — Provision a demo tenant**

In a second terminal, from the `demo/demo-authserver` directory:

```bash
./scripts/setup-tenant.sh
```

The script:
1. Waits for Keycloak and ACA-Py to be ready
2. Obtains a Keycloak admin token
3. Obtains an ACA-Py admin token using the `acapy-controller` client credentials
4. Creates a sub-wallet via `POST /multitenancy/wallet`
5. Updates the `wallet_id` hardcoded claim on the `acapy-tenant-demo` Keycloak client to the new wallet's UUID

On success it prints the token commands to use for the next steps.

## Trying It Out

### Get an admin token

```bash
ADMIN_TOKEN=$(curl -s -X POST \
  'http://localhost:8080/realms/acapy/protocol/openid-connect/token' \
  -d 'grant_type=client_credentials' \
  -d 'client_id=acapy-controller' \
  -d 'client_secret=controller-secret' \
  | jq -r .access_token)
```

Inspect the token to see the `acapy:admin` scope and `acapy-resource-server` audience:

```bash
echo $ADMIN_TOKEN | cut -d. -f2 | base64 -d 2>/dev/null | jq '{scope, aud, sub}'
```

### Call ACA-Py with the admin token

```bash
# List wallets (admin-only)
curl -s -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8031/multitenancy/wallets | jq .

# Check server status
curl -s -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8031/status | jq .
```

### Get a tenant token

```bash
TENANT_TOKEN=$(curl -s -X POST \
  'http://localhost:8080/realms/acapy/protocol/openid-connect/token' \
  -d 'grant_type=client_credentials' \
  -d 'client_id=acapy-tenant-demo' \
  -d 'client_secret=tenant-secret' \
  | jq -r .access_token)
```

The tenant token will contain `acapy:tenant` scope and the `wallet_id` claim set to the provisioned wallet's UUID. ACA-Py uses that claim to route the request to the correct sub-wallet.

```bash
# List connections for the tenant wallet
curl -s -H "Authorization: Bearer $TENANT_TOKEN" \
  http://localhost:8031/connections | jq .
```

### OpenAPI / Swagger UI

Browse to [http://localhost:8031/api/doc](http://localhost:8031/api/doc). Click **Authorize** and paste a bearer token (without the `Bearer ` prefix) to authenticate Swagger requests.

## Configuration

All defaults are in `.env`. Override them by editing the file or exporting variables before running `docker compose up`.

| Variable | Default | Description |
|---|---|---|
| `KEYCLOAK_ADMIN` | `admin` | Keycloak admin username |
| `KEYCLOAK_ADMIN_PASSWORD` | `admin` | Keycloak admin password |
| `KEYCLOAK_PORT` | `8080` | Host port for Keycloak |
| `POSTGRES_USER` | `acapy` | PostgreSQL username |
| `POSTGRES_PASSWORD` | `acapy-secret` | PostgreSQL password |
| `ACAPY_ADMIN_PORT` | `8031` | Host port for ACA-Py admin API |
| `ACAPY_HTTP_PORT` | `8001` | Host port for ACA-Py agent transport |
| `ACAPY_OAUTH_AUDIENCE` | `acapy-resource-server` | Expected `aud` claim in access tokens |
| `ACAPY_WALLET_KEY` | `demo-base-wallet-key` | Base wallet encryption key |
| `ACAPY_LOG_LEVEL` | `info` | ACA-Py log level |

## Adding More Tenants

To provision additional tenants:

1. Create a new confidential client in Keycloak (via the admin console at [http://localhost:8080](http://localhost:8080)) with:
   - Service accounts enabled
   - Default scope: `acapy:tenant`
   - An audience mapper pointing to `acapy-resource-server`
   - A `wallet_id` hardcoded claim (set after wallet creation)
2. Create a sub-wallet via `POST /multitenancy/wallet` using an admin token.
3. Update the client's `wallet_id` claim to the returned wallet UUID.

Or use the `setup-tenant.sh` script as a template — it performs exactly these steps for the `acapy-tenant-demo` client.

## Resetting the Demo

```bash
docker compose down -v   # removes all containers and the wallet-db volume
docker compose up --build
./scripts/setup-tenant.sh
```

The Keycloak realm is reimported from `keycloak/realm-export.json` on each fresh start (Keycloak 24 dev mode uses an in-memory H2 database).

## Token Validation Notes

- ACA-Py validates JWT access tokens locally by fetching signing keys from Keycloak's JWKS endpoint (`/realms/acapy/protocol/openid-connect/certs`). No round-trip to Keycloak occurs on every request — keys are cached by `PyJWKClient` and only re-fetched when a new `kid` is seen.
- The `--jwt-secret` startup parameter is still required by the multitenant subsystem but is **not used** for token issuance or validation when OAuth mode is active.
- Only **managed wallets** (`key_management_mode: managed`) work in OAuth mode. Unmanaged wallets require the wallet key to be passed in the token, which is incompatible with external AS-issued tokens.
