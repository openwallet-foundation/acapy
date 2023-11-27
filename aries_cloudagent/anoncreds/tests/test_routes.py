from asynctest import mock as async_mock, TestCase as AsyncTestCase
from .. import routes as test_module


class TestAnoncredsRoutes(AsyncTestCase):
    async def test_register(self):
        mock_app = async_mock.MagicMock()
        mock_app.add_routes = async_mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()

    async def test_post_process_routes(self):
        mock_app = async_mock.MagicMock(_state={"swagger_dict": {}})
        test_module.post_process_routes(mock_app)
        assert "tags" in mock_app._state["swagger_dict"]


"""
Include a test for each route:

- schemas_post()
- schema_get()
- schemas_get()
- cred_def_post()
- cred_def_get()
- cred_defs_get()
- etc ...

For example see unit tests for routes under:
- aries_cloudagent/messaging/schemas
- aries_cloudagent/messaging/credential_definitions
- etc ...
"""
