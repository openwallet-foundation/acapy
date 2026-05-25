"""OAuth2 token validator for ACA-Py acting as a Resource Server."""

import logging
from typing import Optional

import aiohttp
import jwt
from aiohttp import web

LOGGER = logging.getLogger(__name__)

_SUPPORTED_ALGORITHMS = [
    "RS256", "RS384", "RS512",
    "ES256", "ES384", "ES512",
    "PS256", "PS384", "PS512",
]


class OAuthTokenValidator:
    """Validate OAuth2 bearer tokens from an external Authorization Server.

    Supports JWT access tokens validated locally via JWKS, with opaque token
    fallback via RFC 7662 token introspection.
    """

    def __init__(self, settings):
        """Initialize the validator from application settings."""
        self.jwks_uri: Optional[str] = settings.get("oauth.jwks_uri")
        self.issuer: Optional[str] = settings.get("oauth.issuer")
        self.audience: Optional[str] = settings.get("oauth.audience")
        self.introspection_endpoint: Optional[str] = settings.get(
            "oauth.introspection_endpoint"
        )
        self.introspection_client_id: Optional[str] = settings.get(
            "oauth.introspection_client_id"
        )
        self.introspection_client_secret: Optional[str] = settings.get(
            "oauth.introspection_client_secret"
        )

        # PyJWKClient handles JWKS fetching and caching internally.
        self._jwks_client = (
            jwt.PyJWKClient(self.jwks_uri, cache_keys=True) if self.jwks_uri else None
        )

    async def validate(self, token: str) -> dict:
        """Validate an access token and return its claims.

        Tries JWT validation via JWKS first; falls back to introspection if the
        token is opaque or if JWKS is not configured.

        Raises:
            web.HTTPUnauthorized: If the token is invalid or inactive.

        Returns:
            dict: Validated token claims.
        """
        if self._jwks_client:
            try:
                return self._validate_jwt(token)
            except jwt.exceptions.PyJWKClientError as exc:
                # JWKS infrastructure error — only fall through if introspection is
                # configured as a fallback, otherwise the token cannot be validated.
                if not self.introspection_endpoint:
                    raise web.HTTPUnauthorized(reason="Token validation failed") from exc
                LOGGER.debug("JWKS lookup failed, falling back to introspection: %s", exc)
            except jwt.DecodeError:
                # Token is not a JWT — only meaningful if introspection is available.
                if not self.introspection_endpoint:
                    raise web.HTTPUnauthorized(reason="Invalid token")
                LOGGER.debug("JWT decode failed, falling back to introspection")
            except jwt.InvalidTokenError as exc:
                raise web.HTTPUnauthorized(reason=str(exc)) from exc

        if self.introspection_endpoint:
            return await self._introspect(token)

        raise web.HTTPUnauthorized(
            reason="No token validation method available — configure oauth.jwks_uri or "
            "oauth.introspection_endpoint"
        )

    def _validate_jwt(self, token: str) -> dict:
        """Validate a JWT access token using the configured JWKS endpoint."""
        signing_key = self._jwks_client.get_signing_key_from_jwt(token)

        decode_kwargs = dict(
            algorithms=_SUPPORTED_ALGORITHMS,
            options={"require": ["exp", "iss", "sub"]},
        )
        if self.issuer:
            decode_kwargs["issuer"] = self.issuer
        if self.audience:
            decode_kwargs["audience"] = self.audience

        return jwt.decode(token, signing_key.key, **decode_kwargs)

    async def _introspect(self, token: str) -> dict:
        """Validate an opaque token via RFC 7662 introspection."""
        auth = None
        if self.introspection_client_id:
            auth = aiohttp.BasicAuth(
                self.introspection_client_id,
                self.introspection_client_secret or "",
            )

        async with aiohttp.ClientSession() as session:
            resp = await session.post(
                self.introspection_endpoint,
                data={"token": token, "token_type_hint": "access_token"},
                auth=auth,
            )
            if resp.status != 200:
                raise web.HTTPUnauthorized(
                    reason=f"Token introspection returned HTTP {resp.status}"
                )
            body = await resp.json()

        if not body.get("active"):
            raise web.HTTPUnauthorized(reason="Token is not active")

        return body
