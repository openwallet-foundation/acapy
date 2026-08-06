"""OAuth2 Resource Server scenario.

Drives ACA-Py running as an OAuth2 Resource Server against a Keycloak
Authorization Server:

1. Obtains an admin token (client credentials) and provisions a tenant
   sub-wallet.
2. Wires the new wallet_id into the Keycloak tenant clients' hardcoded claim so
   their tokens route to that wallet.
3. Asserts the scope-enforcement matrix: unauthenticated / invalid tokens are
   rejected, admin scope reaches admin routes, tenant scope is confined to
   tenant routes, and the acapy:wallet:create scope gates wallet creation.

Exits non-zero (failing the scenario) if any assertion does not hold.
"""

import asyncio
from os import getenv

from aiohttp import ClientSession

KEYCLOAK_URL = getenv("KEYCLOAK_URL", "http://keycloak:8080")
ACAPY_ADMIN = getenv("ACAPY_ADMIN", "http://acapy:3001")
REALM = getenv("KEYCLOAK_REALM", "acapy")

REALM_URL = f"{KEYCLOAK_URL}/realms/{REALM}"
TOKEN_ENDPOINT = f"{REALM_URL}/protocol/openid-connect/token"
KC_ADMIN_URL = f"{KEYCLOAK_URL}/admin/realms/{REALM}"

# Clients defined in the imported realm (client_id -> secret).
CONTROLLER = ("acapy-controller", "controller-secret")  # acapy:admin
TENANT = ("acapy-tenant-demo", "tenant-secret")  # acapy:tenant + wallet:create
LIMITED = ("acapy-tenant-limited", "limited-secret")  # acapy:tenant only

DID_CREATE_BODY = {"method": "key", "options": {"key_type": "ed25519"}}


class ScenarioError(Exception):
    """Raised when an assertion in the scenario fails."""


async def _wait_for_keycloak(session: ClientSession, attempts: int = 60, delay: int = 3):
    """Poll Keycloak until the realm is imported and issuing tokens.

    ACA-Py only waits for the Keycloak container to start, so the realm import
    may still be in progress when this container launches.
    """
    for attempt in range(1, attempts + 1):
        try:
            await _client_credentials_token(session, *CONTROLLER)
            print(f"==> Keycloak ready (attempt {attempt})")
            return
        except Exception as err:  # noqa: BLE001 - readiness poll, any error retries
            if attempt == attempts:
                raise ScenarioError(
                    f"Keycloak not ready after {attempts} attempts: {err}"
                )
            await asyncio.sleep(delay)


async def _client_credentials_token(session: ClientSession, client_id, secret) -> str:
    async with session.post(
        TOKEN_ENDPOINT,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": secret,
        },
    ) as resp:
        resp.raise_for_status()
        body = await resp.json()
    return body["access_token"]


async def _keycloak_admin_token(session: ClientSession) -> str:
    async with session.post(
        f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": "admin",
            "password": "admin",
        },
    ) as resp:
        resp.raise_for_status()
        body = await resp.json()
    return body["access_token"]


async def _status(session: ClientSession, method: str, path: str, token=None, json=None):
    """Return the HTTP status of an admin API call."""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with session.request(
        method, f"{ACAPY_ADMIN}{path}", headers=headers, json=json
    ) as resp:
        return resp.status


async def _provision_wallet(session: ClientSession, admin_token: str) -> str:
    """Create a tenant sub-wallet and return its wallet_id."""
    async with session.post(
        f"{ACAPY_ADMIN}/multitenancy/wallet",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "label": "scenario-tenant",
            "wallet_name": "scenario-tenant",
            "wallet_type": "askar",
            "wallet_key": "scenario-tenant-key",
            "key_management_mode": "managed",
        },
    ) as resp:
        resp.raise_for_status()
        body = await resp.json()
    return body["wallet_id"]


async def _set_wallet_id_claim(
    session: ClientSession, kc_admin_token: str, client_id: str, wallet_id: str
):
    """Point the client's wallet-id hardcoded-claim mapper at wallet_id."""
    headers = {"Authorization": f"Bearer {kc_admin_token}"}
    async with session.get(
        f"{KC_ADMIN_URL}/clients", headers=headers, params={"clientId": client_id}
    ) as resp:
        resp.raise_for_status()
        clients = await resp.json()
    client_uuid = clients[0]["id"]

    mappers_url = f"{KC_ADMIN_URL}/clients/{client_uuid}/protocol-mappers/models"
    async with session.get(mappers_url, headers=headers) as resp:
        resp.raise_for_status()
        mappers = await resp.json()
    mapper = next(m for m in mappers if m["name"] == "wallet-id")
    mapper["config"]["claim.value"] = wallet_id
    async with session.put(
        f"{mappers_url}/{mapper['id']}", headers=headers, json=mapper
    ) as resp:
        resp.raise_for_status()


def _expect(label: str, actual: int, expected: int):
    status = "PASS" if actual == expected else "FAIL"
    print(f"  [{status}] {label}: expected {expected}, got {actual}")
    if actual != expected:
        raise ScenarioError(f"{label}: expected {expected}, got {actual}")


async def main():
    """Run the OAuth2 Resource Server scenario."""
    async with ClientSession() as session:
        await _wait_for_keycloak(session)

        admin_token = await _client_credentials_token(session, *CONTROLLER)
        kc_admin_token = await _keycloak_admin_token(session)

        wallet_id = await _provision_wallet(session, admin_token)
        print(f"==> Provisioned tenant wallet: {wallet_id}")
        for client_id, _ in (TENANT, LIMITED):
            await _set_wallet_id_claim(session, kc_admin_token, client_id, wallet_id)

        tenant_token = await _client_credentials_token(session, *TENANT)
        limited_token = await _client_credentials_token(session, *LIMITED)

        print("Unauthenticated / invalid tokens are rejected:")
        _expect(
            "GET /multitenancy/wallets no token",
            await _status(session, "GET", "/multitenancy/wallets"),
            401,
        )
        _expect(
            "GET /connections no token",
            await _status(session, "GET", "/connections"),
            401,
        )
        _expect(
            "GET /connections invalid token",
            await _status(session, "GET", "/connections", token="not-a-jwt"),
            401,
        )

        print("Admin scope reaches admin routes:")
        _expect(
            "GET /status/config admin",
            await _status(session, "GET", "/status/config", token=admin_token),
            200,
        )
        _expect(
            "GET /multitenancy/wallets admin",
            await _status(session, "GET", "/multitenancy/wallets", token=admin_token),
            200,
        )
        _expect(
            "POST /wallet/did/create admin",
            await _status(
                session, "POST", "/wallet/did/create", admin_token, DID_CREATE_BODY
            ),
            200,
        )

        print("Tenant scope is confined to tenant routes:")
        _expect(
            "GET /connections tenant",
            await _status(session, "GET", "/connections", token=tenant_token),
            200,
        )
        _expect(
            "GET /multitenancy/wallets tenant (admin only)",
            await _status(session, "GET", "/multitenancy/wallets", token=tenant_token),
            403,
        )
        _expect(
            "POST /wallet/did/create tenant (has wallet:create)",
            await _status(
                session, "POST", "/wallet/did/create", tenant_token, DID_CREATE_BODY
            ),
            200,
        )

        print("acapy:wallet:create scope gates DID creation:")
        _expect(
            "GET /connections limited",
            await _status(session, "GET", "/connections", token=limited_token),
            200,
        )
        _expect(
            "POST /wallet/did/create limited (no wallet:create)",
            await _status(
                session, "POST", "/wallet/did/create", limited_token, DID_CREATE_BODY
            ),
            403,
        )

        print("All OAuth Resource Server scope assertions passed.")


if __name__ == "__main__":
    asyncio.run(main())
