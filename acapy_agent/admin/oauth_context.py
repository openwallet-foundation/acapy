"""OAuth2 request authentication for the admin API.

Keeps the OAuth Resource Server request and websocket authorization logic out
of the admin server module. An instance is created by ``AdminServer`` when
OAuth mode is active.
"""

from typing import Tuple

from aiohttp import web

from ..config.logging import context_wallet_id
from ..storage.error import StorageNotFoundError
from ..wallet.models.wallet_record import WalletRecord
from . import scopes
from .auth_context import (
    AUTH_SCOPES_SETTING,
    AUTH_SUBJECT_SETTING,
    AUTH_WALLET_ID_SETTING,
)


class OAuthRequestAuthenticator:
    """Authenticate admin API requests and websockets against OAuth2 tokens."""

    def __init__(self, validator, multitenant_manager, root_profile, context):
        """Initialize the authenticator with the collaborators it needs."""
        self.validator = validator
        self.multitenant_manager = multitenant_manager
        self.root_profile = root_profile
        self.context = context

    async def authenticate_request(self, authorization_header: str) -> Tuple:
        """Validate the bearer token and derive the request profile/context.

        Args:
            authorization_header: the raw ``Authorization`` header value.

        Returns:
            A ``(profile, meta_data, request_settings)`` tuple for building the
            request's ``AdminRequestContext``.

        Raises:
            web.HTTPUnauthorized: the header is malformed, the token is invalid,
                or (in multitenant mode) the token lacks a ``wallet_id`` claim
                without carrying the admin scope.

        """
        bearer, _, token = authorization_header.partition(" ")
        if bearer != "Bearer":
            raise web.HTTPUnauthorized(reason="Invalid Authorization header structure")

        claims = await self.validator.validate(token)
        token_scopes = set(claims.get("scope", "").split())
        meta_data = {"scopes": token_scopes, "sub": claims.get("sub")}
        request_settings = {AUTH_SCOPES_SETTING: tuple(sorted(token_scopes))}
        if claims.get("sub"):
            request_settings[AUTH_SUBJECT_SETTING] = claims["sub"]

        profile = self.root_profile
        if self.multitenant_manager:
            profile = await self._resolve_wallet_profile(
                claims, token_scopes, meta_data, request_settings
            )
        return profile, meta_data, request_settings

    async def _resolve_wallet_profile(
        self, claims, token_scopes, meta_data, request_settings
    ):
        """Select the sub-wallet profile from the token's ``wallet_id`` claim."""
        wallet_id = claims.get("wallet_id")
        if not wallet_id:
            if scopes.ADMIN not in token_scopes:
                # Without a wallet_id claim the request would run against the
                # base wallet; only admin-scoped tokens may do that.
                raise web.HTTPUnauthorized(
                    reason=(
                        "Token must include a wallet_id claim (or the "
                        "acapy:admin scope) in multitenant mode"
                    )
                )
            return self.root_profile

        try:
            async with self.root_profile.session() as session:
                wallet = await WalletRecord.retrieve_by_id(session, wallet_id)
            profile = await self.multitenant_manager.get_wallet_profile(
                self.context, wallet
            )
        except StorageNotFoundError:
            raise web.HTTPUnauthorized(
                reason=f"Wallet not found for wallet_id claim: {wallet_id}"
            )
        context_wallet_id.set(wallet_id)
        meta_data["wallet_id"] = wallet_id
        request_settings[AUTH_WALLET_ID_SETTING] = wallet_id
        return profile

    def authorize_websocket(self, claims: dict, queue) -> None:
        """Set websocket authorization on the queue from validated token claims.

        Mirrors the HTTP auth decorators so the admin event stream honours the
        same scope and tenant-isolation rules:

        - ``acapy:admin`` receives the full cross-wallet event stream.
        - ``acapy:tenant`` / ``acapy:tenant:read`` receives only its own
          wallet's events; in multitenant mode a ``wallet_id`` claim is
          required.
        - Any other token is treated as unauthenticated (no events delivered).
        """
        token_scopes = set(claims.get("scope", "").split())
        wallet_id = claims.get("wallet_id")

        if scopes.ADMIN in token_scopes:
            queue.authenticated = True
            queue.receive_all = True
        elif token_scopes & {scopes.TENANT, scopes.TENANT_READ}:
            if self.multitenant_manager and not wallet_id:
                # A tenant token with no wallet binding must not receive events.
                queue.authenticated = False
            else:
                queue.authenticated = True
                queue.wallet_id = wallet_id
                queue.receive_all = not self.multitenant_manager
        else:
            queue.authenticated = False
