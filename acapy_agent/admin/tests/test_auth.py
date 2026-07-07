from unittest import IsolatedAsyncioTestCase

from aiohttp import web

from ...tests import mock
from ...utils.testing import create_test_profile
from ..decorators.auth import admin_authentication, require_scope, tenant_authentication
from ..request_context import AdminRequestContext


class TestAdminAuthentication(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.profile = await create_test_profile(
            settings={
                "admin.admin_api_key": "admin_api_key",
                "admin.admin_insecure_mode": False,
            }
        )
        self.context = AdminRequestContext.test_context({}, self.profile)
        self.request_dict = {
            "context": self.context,
        }
        self.request = mock.MagicMock(
            __getitem__=lambda _, k: self.request_dict[k], headers={}, method="POST"
        )
        self.decorated_handler = mock.CoroutineMock()

    async def test_options_request(self):
        self.request = mock.MagicMock(
            __getitem__=lambda _, k: self.request_dict[k], headers={}, method="OPTIONS"
        )
        decor_func = admin_authentication(self.decorated_handler)
        await decor_func(self.request)
        self.decorated_handler.assert_called_once_with(self.request)

    async def test_insecure_mode(self):
        self.profile.settings["admin.admin_insecure_mode"] = True
        decor_func = admin_authentication(self.decorated_handler)
        await decor_func(self.request)
        self.decorated_handler.assert_called_once_with(self.request)

    async def test_invalid_api_key(self):
        self.request = mock.MagicMock(
            __getitem__=lambda _, k: self.request_dict[k],
            headers={"x-api-key": "wrong-key"},
            method="POST",
        )
        decor_func = admin_authentication(self.decorated_handler)
        with self.assertRaises(web.HTTPUnauthorized):
            await decor_func(self.request)

    async def test_valid_api_key(self):
        self.request = mock.MagicMock(
            __getitem__=lambda _, k: self.request_dict[k],
            headers={"x-api-key": "admin_api_key"},
            method="POST",
        )
        decor_func = admin_authentication(self.decorated_handler)
        await decor_func(self.request)
        self.decorated_handler.assert_called_once_with(self.request)

    def _make_oauth_request(self, scopes, method="POST"):
        context = AdminRequestContext(
            profile=self.profile, metadata={"scopes": set(scopes)}
        )
        return mock.MagicMock(
            __getitem__=lambda _, k: {"context": context}[k],
            headers={},
            method=method,
        )

    async def test_oauth_admin_scope_allowed(self):
        request = self._make_oauth_request(["acapy:admin"])
        decor_func = admin_authentication(self.decorated_handler)
        await decor_func(request)
        self.decorated_handler.assert_called_once_with(request)

    async def test_oauth_tenant_scope_forbidden(self):
        request = self._make_oauth_request(["acapy:tenant"])
        decor_func = admin_authentication(self.decorated_handler)
        with self.assertRaises(web.HTTPForbidden):
            await decor_func(request)

    async def test_oauth_no_scopes_forbidden(self):
        request = self._make_oauth_request([])
        decor_func = admin_authentication(self.decorated_handler)
        with self.assertRaises(web.HTTPForbidden):
            await decor_func(request)


class TestTenantAuthentication(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.profile = await create_test_profile(
            settings={
                "admin.admin_api_key": "admin_api_key",
                "admin.admin_insecure_mode": False,
                "multitenant.enabled": True,
            }
        )
        self.context = AdminRequestContext.test_context({}, self.profile)
        self.request_dict = {
            "context": self.context,
        }
        self.request = mock.MagicMock(
            __getitem__=lambda _, k: self.request_dict[k], headers={}, method="POST"
        )
        self.decorated_handler = mock.CoroutineMock()

    async def test_options_request(self):
        self.request = mock.MagicMock(
            __getitem__=lambda _, k: self.request_dict[k], headers={}, method="OPTIONS"
        )
        decor_func = tenant_authentication(self.decorated_handler)
        await decor_func(self.request)
        self.decorated_handler.assert_called_once_with(self.request)

    async def test_insecure_mode_witout_token(self):
        self.profile.settings["admin.admin_insecure_mode"] = True
        decor_func = tenant_authentication(self.decorated_handler)
        with self.assertRaises(web.HTTPUnauthorized):
            await decor_func(self.request)

    async def test_single_tenant_invalid_api_key(self):
        self.profile.settings["multitenant.enabled"] = False
        self.request = mock.MagicMock(
            __getitem__=lambda _, k: self.request_dict[k],
            headers={"x-api-key": "wrong-key"},
            method="POST",
        )
        decor_func = tenant_authentication(self.decorated_handler)
        with self.assertRaises(web.HTTPUnauthorized):
            await decor_func(self.request)

    async def test_single_tenant_valid_api_key(self):
        self.profile.settings["multitenant.enabled"] = False
        self.request = mock.MagicMock(
            __getitem__=lambda _, k: self.request_dict[k],
            headers={"x-api-key": "admin_api_key"},
            method="POST",
        )
        decor_func = tenant_authentication(self.decorated_handler)
        await decor_func(self.request)
        self.decorated_handler.assert_called_once_with(self.request)

    async def test_multi_tenant_missing_auth_header(self):
        self.request = mock.MagicMock(
            __getitem__=lambda _, k: self.request_dict[k],
            headers={"x-api-key": "wrong-key"},
            method="POST",
        )
        decor_func = tenant_authentication(self.decorated_handler)
        with self.assertRaises(web.HTTPUnauthorized):
            await decor_func(self.request)

    async def test_multi_tenant_valid_auth_header(self):
        self.request = mock.MagicMock(
            __getitem__=lambda _, k: self.request_dict[k],
            headers={"x-api-key": "admin_api_key", "Authorization": "Bearer my-jwt"},
            method="POST",
        )
        decor_func = tenant_authentication(self.decorated_handler)
        await decor_func(self.request)
        self.decorated_handler.assert_called_once_with(self.request)

    async def test_base_wallet_additional_route_allowed_string(self):
        self.profile.settings["multitenant.base_wallet_routes"] = (
            "/not-this-route /extra-route"
        )
        self.request = mock.MagicMock(
            __getitem__=lambda _, k: self.request_dict[k],
            headers={"x-api-key": "admin_api_key"},
            method="POST",
            path="/extra-route",
        )
        decor_func = tenant_authentication(self.decorated_handler)
        await decor_func(self.request)
        self.decorated_handler.assert_called_once_with(self.request)

    async def test_base_wallet_additional_route_allowed_list(self):
        self.profile.settings["multitenant.base_wallet_routes"] = [
            "/extra-route",
            "/not-this-route",
        ]
        self.request = mock.MagicMock(
            __getitem__=lambda _, k: self.request_dict[k],
            headers={"x-api-key": "admin_api_key"},
            method="POST",
            path="/extra-route",
        )
        decor_func = tenant_authentication(self.decorated_handler)
        await decor_func(self.request)
        self.decorated_handler.assert_called_once_with(self.request)

    async def test_base_wallet_additional_route_denied(self):
        self.profile.settings["multitenant.base_wallet_routes"] = "/extra-route"
        self.request = mock.MagicMock(
            __getitem__=lambda _, k: self.request_dict[k],
            headers={"x-api-key": "admin_api_key"},
            method="POST",
            path="/extra-route-wrong",
        )
        decor_func = tenant_authentication(self.decorated_handler)
        with self.assertRaises(web.HTTPUnauthorized):
            await decor_func(self.request)

    def _make_oauth_request(self, scopes, method="POST"):
        context = AdminRequestContext(
            profile=self.profile, metadata={"scopes": set(scopes)}
        )
        return mock.MagicMock(
            __getitem__=lambda _, k: {"context": context}[k],
            headers={},
            method=method,
        )

    async def test_oauth_tenant_scope_allowed(self):
        request = self._make_oauth_request(["acapy:tenant"])
        decor_func = tenant_authentication(self.decorated_handler)
        await decor_func(request)
        self.decorated_handler.assert_called_once_with(request)

    async def test_oauth_admin_scope_allowed_on_tenant_route(self):
        request = self._make_oauth_request(["acapy:admin"])
        decor_func = tenant_authentication(self.decorated_handler)
        await decor_func(request)
        self.decorated_handler.assert_called_once_with(request)

    async def test_oauth_read_scope_allows_get(self):
        request = self._make_oauth_request(["acapy:tenant:read"], method="GET")
        decor_func = tenant_authentication(self.decorated_handler)
        await decor_func(request)
        self.decorated_handler.assert_called_once_with(request)

    async def test_oauth_read_scope_forbids_write(self):
        request = self._make_oauth_request(["acapy:tenant:read"], method="POST")
        decor_func = tenant_authentication(self.decorated_handler)
        with self.assertRaises(web.HTTPForbidden):
            await decor_func(request)

    async def test_oauth_unrelated_scope_forbidden(self):
        request = self._make_oauth_request(["profile email"])
        decor_func = tenant_authentication(self.decorated_handler)
        with self.assertRaises(web.HTTPForbidden):
            await decor_func(request)


class TestRequireScope(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.profile = await create_test_profile()
        self.decorated_handler = mock.CoroutineMock()

    def _make_request(self, scopes=None, method="POST"):
        metadata = {"scopes": set(scopes)} if scopes is not None else None
        context = AdminRequestContext(profile=self.profile, metadata=metadata)
        return mock.MagicMock(
            __getitem__=lambda _, k: {"context": context}[k],
            headers={},
            method=method,
        )

    async def test_options_always_passes(self):
        request = self._make_request(method="OPTIONS")
        decor = require_scope("acapy:tenant")(self.decorated_handler)
        await decor(request)
        self.decorated_handler.assert_called_once_with(request)

    async def test_non_oauth_mode_passes_without_scopes(self):
        """require_scope is a no-op when admin.oauth_enabled is not set."""
        request = self._make_request()  # no metadata / no scopes
        decor = require_scope("acapy:tenant")(self.decorated_handler)
        await decor(request)
        self.decorated_handler.assert_called_once_with(request)

    async def test_oauth_mode_passes_with_required_scope(self):
        self.profile.settings["admin.oauth_enabled"] = True
        request = self._make_request(scopes=["acapy:tenant"])
        decor = require_scope("acapy:tenant", "acapy:admin")(self.decorated_handler)
        await decor(request)
        self.decorated_handler.assert_called_once_with(request)

    async def test_oauth_mode_admin_scope_satisfies_any_requirement(self):
        self.profile.settings["admin.oauth_enabled"] = True
        request = self._make_request(scopes=["acapy:admin"])
        decor = require_scope("acapy:wallet:create", "acapy:admin")(
            self.decorated_handler
        )
        await decor(request)
        self.decorated_handler.assert_called_once_with(request)

    async def test_oauth_mode_raises_403_on_insufficient_scope(self):
        self.profile.settings["admin.oauth_enabled"] = True
        request = self._make_request(scopes=["acapy:tenant:read"])
        decor = require_scope("acapy:wallet:create", "acapy:admin")(
            self.decorated_handler
        )
        with self.assertRaises(web.HTTPForbidden):
            await decor(request)

    async def test_oauth_mode_raises_403_when_no_scopes_in_token(self):
        self.profile.settings["admin.oauth_enabled"] = True
        request = self._make_request(scopes=[])
        decor = require_scope("acapy:tenant")(self.decorated_handler)
        with self.assertRaises(web.HTTPForbidden):
            await decor(request)
