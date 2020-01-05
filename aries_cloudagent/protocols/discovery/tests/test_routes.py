from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from ....storage.error import StorageNotFoundError

from .. import routes as test_module


class TestBasicMessageRoutes(AsyncTestCase):
    async def test_query_features(self):
        mock_request = async_mock.MagicMock(query=async_mock.MagicMock())
        mock_request.json = async_mock.CoroutineMock()

        mock_context = async_mock.MagicMock()
        mock_context.inject = async_mock.CoroutineMock()
        mock_context.inject.return_value = async_mock.MagicMock()
        mock_query = async_mock.MagicMock(
            return_value=["abc", "def", "ghi"]
        )
        mock_context.inject.return_value.protocols_matching_query = mock_query

        mock_request.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": mock_context,
        }

        with async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:

            res = await test_module.query_features(mock_request)
            mock_response.assert_called_once_with(
                {
                    "results": {
                        k: {} for k in mock_query.return_value
                    }
                }
            )

    async def test_register(self):
        mock_app = async_mock.MagicMock()
        mock_app.add_routes = async_mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()

