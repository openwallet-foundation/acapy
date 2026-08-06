"""Tests for the OAuth2 request authenticator."""

from unittest import IsolatedAsyncioTestCase

from aiohttp import web

from ...storage.error import StorageNotFoundError
from ...tests import mock
from .. import oauth_context
from ..auth_context import (
    AUTH_SCOPES_SETTING,
    AUTH_SUBJECT_SETTING,
    AUTH_WALLET_ID_SETTING,
)
from ..oauth_context import OAuthRequestAuthenticator


def make_authenticator(claims=None, multitenant=False, validate_exc=None):
    validator = mock.MagicMock()
    if validate_exc is not None:
        validator.validate = mock.CoroutineMock(side_effect=validate_exc)
    else:
        validator.validate = mock.CoroutineMock(return_value=claims or {})
    manager = mock.MagicMock() if multitenant else None
    root_profile = mock.MagicMock()
    context = mock.MagicMock()
    return (
        OAuthRequestAuthenticator(validator, manager, root_profile, context),
        validator,
        manager,
        root_profile,
    )


class TestAuthenticateRequest(IsolatedAsyncioTestCase):
    async def test_malformed_header_rejected(self):
        auth, *_ = make_authenticator(claims={"scope": "acapy:admin"})
        with self.assertRaises(web.HTTPUnauthorized):
            await auth.authenticate_request("Basic dXNlcjpwYXNz")

    async def test_single_tenant_returns_root_profile_and_metadata(self):
        auth, _, _, root_profile = make_authenticator(
            claims={"scope": "acapy:admin", "sub": "svc-1"}
        )
        profile, meta, settings = await auth.authenticate_request("Bearer tok")
        assert profile is root_profile
        assert meta["scopes"] == {"acapy:admin"}
        assert meta["sub"] == "svc-1"
        assert settings[AUTH_SCOPES_SETTING] == ("acapy:admin",)
        assert settings[AUTH_SUBJECT_SETTING] == "svc-1"

    async def test_no_sub_omits_subject_setting(self):
        auth, *_ = make_authenticator(claims={"scope": "acapy:admin"})
        _, meta, settings = await auth.authenticate_request("Bearer tok")
        assert meta["sub"] is None
        assert AUTH_SUBJECT_SETTING not in settings

    async def test_multitenant_wallet_id_selects_profile(self):
        auth, _, manager, root_profile = make_authenticator(
            claims={"scope": "acapy:tenant", "wallet_id": "wallet-A"},
            multitenant=True,
        )
        wallet_profile = mock.MagicMock()
        manager.get_wallet_profile = mock.CoroutineMock(return_value=wallet_profile)
        with mock.patch.object(
            oauth_context.WalletRecord,
            "retrieve_by_id",
            mock.CoroutineMock(return_value=mock.MagicMock()),
        ) as mock_retrieve:
            profile, meta, settings = await auth.authenticate_request("Bearer tok")
        assert profile is wallet_profile
        assert mock_retrieve.call_args.args[1] == "wallet-A"
        assert meta["wallet_id"] == "wallet-A"
        assert settings[AUTH_WALLET_ID_SETTING] == "wallet-A"

    async def test_multitenant_unknown_wallet_id_rejected(self):
        auth, _, manager, _ = make_authenticator(
            claims={"scope": "acapy:tenant", "wallet_id": "nope"},
            multitenant=True,
        )
        with mock.patch.object(
            oauth_context.WalletRecord,
            "retrieve_by_id",
            mock.CoroutineMock(side_effect=StorageNotFoundError()),
        ):
            with self.assertRaises(web.HTTPUnauthorized):
                await auth.authenticate_request("Bearer tok")

    async def test_multitenant_missing_wallet_id_rejected_for_non_admin(self):
        auth, *_ = make_authenticator(claims={"scope": "acapy:tenant"}, multitenant=True)
        with self.assertRaises(web.HTTPUnauthorized):
            await auth.authenticate_request("Bearer tok")

    async def test_multitenant_missing_wallet_id_allowed_for_admin(self):
        auth, _, _, root_profile = make_authenticator(
            claims={"scope": "acapy:admin"}, multitenant=True
        )
        profile, _, _ = await auth.authenticate_request("Bearer tok")
        assert profile is root_profile

    async def test_invalid_token_propagates(self):
        auth, *_ = make_authenticator(
            validate_exc=web.HTTPUnauthorized(reason="bad token")
        )
        with self.assertRaises(web.HTTPUnauthorized):
            await auth.authenticate_request("Bearer tok")


class _Queue:
    def __init__(self):
        self.authenticated = False
        self.wallet_id = None
        self.receive_all = True


class TestAuthorizeWebsocket(IsolatedAsyncioTestCase):
    def test_admin_scope_receives_all(self):
        auth, *_ = make_authenticator(multitenant=True)
        queue = _Queue()
        auth.authorize_websocket({"scope": "acapy:admin", "wallet_id": "w1"}, queue)
        assert queue.authenticated is True
        assert queue.receive_all is True

    def test_tenant_scope_scoped_to_wallet(self):
        auth, *_ = make_authenticator(multitenant=True)
        queue = _Queue()
        auth.authorize_websocket(
            {"scope": "acapy:tenant", "wallet_id": "wallet-A"}, queue
        )
        assert queue.authenticated is True
        assert queue.receive_all is False
        assert queue.wallet_id == "wallet-A"

    def test_tenant_scope_without_wallet_rejected(self):
        auth, *_ = make_authenticator(multitenant=True)
        queue = _Queue()
        auth.authorize_websocket({"scope": "acapy:tenant"}, queue)
        assert queue.authenticated is False

    def test_tenant_scope_single_tenant_receives_all(self):
        auth, *_ = make_authenticator(multitenant=False)
        queue = _Queue()
        auth.authorize_websocket({"scope": "acapy:tenant:read"}, queue)
        assert queue.authenticated is True
        assert queue.receive_all is True

    def test_unrecognized_scope_not_authenticated(self):
        auth, *_ = make_authenticator(multitenant=True)
        queue = _Queue()
        auth.authorize_websocket({"scope": "openid profile", "wallet_id": "w"}, queue)
        assert queue.authenticated is False
