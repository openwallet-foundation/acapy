from unittest import IsolatedAsyncioTestCase

import pytest

from ...admin.request_context import AdminRequestContext
from ...tests import mock
from ...utils.testing import create_test_profile
from ..routes import post_process_routes, register


@pytest.mark.anoncreds
class TestAnonCredsRoutes(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.session_inject = {}
        self.profile = await create_test_profile(
            settings={
                "wallet.type": "askar-anoncreds",
                "admin.admin_api_key": "secret-key",
            },
        )
        self.context = AdminRequestContext.test_context(self.session_inject, self.profile)
        self.request_dict = {
            "context": self.context,
        }
        self.request = mock.MagicMock(
            app={},
            match_info={},
            query={},
            __getitem__=lambda _, k: self.request_dict[k],
            context=self.context,
            headers={"x-api-key": "secret-key"},
        )

    async def test_register(self):
        mock_app = mock.MagicMock()
        mock_app.add_routes = mock.MagicMock()

        await register(mock_app)
        assert mock_app.add_routes.call_count == 6  # schema, cred def, and 4 revocation

    async def test_post_process_routes(self):
        mock_app = mock.MagicMock(_state={"swagger_dict": {}})
        post_process_routes(mock_app)
        assert "tags" in mock_app._state["swagger_dict"]
