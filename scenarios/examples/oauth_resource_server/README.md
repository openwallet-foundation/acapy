# OAuth2 Resource Server scenario

Regression test for ACA-Py running as an [OAuth2 Resource
Server](../../../docs/features/OAuthResourceServer.md): an external Keycloak
Authorization Server issues JWT access tokens, and ACA-Py validates them via
JWKS and enforces scope-based access control.

## What it covers

`example.py` provisions a tenant sub-wallet, wires its `wallet_id` into the
Keycloak tenant clients, then asserts the scope-enforcement matrix:

| Caller (scope) | Route | Expected |
|---|---|---|
| no token | protected routes | `401` |
| invalid token | `/connections` | `401` |
| admin (`acapy:admin`) | `/status/config`, `/multitenancy/wallets`, `POST /wallet/did/create` | `200` |
| tenant (`acapy:tenant` + `acapy:wallet:create`) | `/connections`, `POST /wallet/did/create` | `200` |
| tenant | `/multitenancy/wallets` (admin only) | `403` |
| limited (`acapy:tenant`, no `acapy:wallet:create`) | `POST /wallet/did/create` | `403` |

## Running

From the `scenarios` directory (an `acapy-test` image must be built first, as in
CI):

```bash
docker build -t acapy-test -f ../docker/Dockerfile.run ..
poetry run pytest -m examples -k oauth_resource_server
```

On Apple Silicon / arm64, add `--build-arg all_extras=` to the build so it skips
the BBS+ extra (`ursa-bbs-signatures`), which has no arm64 build:

```bash
docker build -t acapy-test -f ../docker/Dockerfile.run --build-arg all_extras= ..
```

The realm (`keycloak/realm-export.json`) defines the resource-server audience,
the client scopes, and the caller clients. It mirrors the human-facing
walkthrough under [`demo/demo-authserver`](../../../demo/demo-authserver); keep
the two realm exports in sync when changing client or scope configuration.
