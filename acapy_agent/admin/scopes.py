"""OAuth2 scope identifiers for the admin API.

Central definitions so scope strings are not duplicated across the auth
decorators, the request authenticator, and route handlers.
"""

ADMIN = "acapy:admin"
TENANT = "acapy:tenant"
TENANT_READ = "acapy:tenant:read"
WALLET_CREATE = "acapy:wallet:create"

# Scopes that grant tenant-level (sub-wallet) access.
TENANT_LEVEL = frozenset({TENANT, ADMIN})
