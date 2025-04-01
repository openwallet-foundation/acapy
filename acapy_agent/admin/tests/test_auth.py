from unittest import IsolatedAsyncioTestCase

from aiohttp import web

from ...tests import mock
from ...utils.testing import create_test_profile
from ..decorators.auth import admin_authentication, tenant_authentication
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
