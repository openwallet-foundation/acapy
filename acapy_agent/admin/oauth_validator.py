"""OAuth2 token validator for ACA-Py acting as a Resource Server."""

import asyncio
import logging
from typing import Optional

import aiohttp
import jwt
from aiohttp import web

LOGGER = logging.getLogger(__name__)

DEFAULT_HTTP_TIMEOUT = 10

_SUPPORTED_ALGORITHMS = [
    "RS256",
    "RS384",
    "RS512",
    "ES256",
    "ES384",
    "ES512",
    "PS256",
    "PS384",
    "PS512",
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
        self.http_timeout: float = (
            settings.get("oauth.http_timeout") or DEFAULT_HTTP_TIMEOUT
        )

        # PyJWKClient handles JWKS fetching and caching internally.
        self._jwks_client = (
            jwt.PyJWKClient(self.jwks_uri, cache_keys=True, timeout=self.http_timeout)
            if self.jwks_uri
            else None
        )

        # Shared HTTP session for introspection calls, created lazily on first
        # use and closed via close().
        self._session: Optional[aiohttp.ClientSession] = None

    def _get_session(self) -> aiohttp.ClientSession:
        """Return the shared introspection HTTP session, creating it if needed."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.http_timeout)
            )
        return self._session

    async def close(self):
        """Release the HTTP session used for introspection calls."""
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None

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
                return await self._validate_jwt(token)
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

    async def _validate_jwt(self, token: str) -> dict:
        """Validate a JWT access token using the configured JWKS endpoint."""
        # PyJWKClient fetches the JWKS synchronously (urllib) on a cache miss;
        # run it in a thread so a slow AS doesn't block the event loop.
        signing_key = await asyncio.get_running_loop().run_in_executor(
            None, self._jwks_client.get_signing_key_from_jwt, token
        )

        decode_kwargs = {
            "algorithms": _SUPPORTED_ALGORITHMS,
            # Without verify_aud=False, PyJWT rejects any token carrying an
            # aud claim when no expected audience is configured.
            "options": {
                "require": ["exp", "iss", "sub"],
                "verify_aud": self.audience is not None,
            },
        }
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

        try:
            async with self._get_session().post(
                self.introspection_endpoint,
                data={"token": token, "token_type_hint": "access_token"},
                auth=auth,
            ) as resp:
                if resp.status != 200:
                    raise web.HTTPUnauthorized(
                        reason=f"Token introspection returned HTTP {resp.status}"
                    )
                body = await resp.json()
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            # The Authorization Server being unreachable is a server-side
            # failure, not a statement about the token's validity.
            LOGGER.warning("Token introspection request failed: %s", exc)
            raise web.HTTPServiceUnavailable(
                reason="Token introspection unavailable"
            ) from exc

        if not body.get("active"):
            raise web.HTTPUnauthorized(reason="Token is not active")

        return body
