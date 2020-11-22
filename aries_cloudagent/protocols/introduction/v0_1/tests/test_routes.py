from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.messaging.request_context import RequestContext

from .. import routes as test_module


class TestIntroductionRoutes(AsyncTestCase):
    def setUp(self):
        self.context = RequestContext(
            base_context=InjectionContext(enforce_typing=False)
        )
        self.mock_request = async_mock.MagicMock(
            __getitem__=async_mock.Mock(
                side_effect={
                    "context": self.context,
                    "outbound_message_router": None,
                }.__getitem__
            ),
        )

    async def test_introduction_start_no_service(self):
        self.mock_request.json = async_mock.CoroutineMock(
            return_value={
                "my_seed": "my_seed",
                "my_did": "my_did",
                "their_seed": "their_seed",
                "their_did": "their_did",
                "their_verkey": "their_verkey",
                "their_endpoint": "their_endpoint",
                "their_role": "their_role",
                "alias": "alias",
            }
        )
        self.mock_request.match_info = {"conn_id": "dummy"}
        self.mock_request.query = {
            "target_connection_id": "dummy",
            "message": "Hello",
        }

        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.introduction_start(self.mock_request)

    async def test_introduction_start(self):
        self.mock_request.json = async_mock.CoroutineMock(
            return_value={
                "my_seed": "my_seed",
                "my_did": "my_did",
                "their_seed": "their_seed",
                "their_did": "their_did",
                "their_verkey": "their_verkey",
                "their_endpoint": "their_endpoint",
                "their_role": "their_role",
                "alias": "alias",
            }
        )
        self.mock_request.match_info = {"conn_id": "dummy"}
        self.mock_request.query = {
            "target_connection_id": "dummy",
            "message": "Hello",
        }
        mock_conn_rec = async_mock.MagicMock()
        mock_conn_rec.serialize = async_mock.MagicMock()

        with async_mock.patch.object(
            self.context, "inject", async_mock.CoroutineMock()
        ) as mock_ctx_inject, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_ctx_inject.return_value = async_mock.MagicMock(
                start_introduction=async_mock.CoroutineMock()
            )

            await test_module.introduction_start(self.mock_request)
            mock_ctx_inject.return_value.start_introduction.assert_called_once_with(
                self.mock_request.match_info["conn_id"],
                self.mock_request.query["target_connection_id"],
                self.mock_request.query["message"],
                self.mock_request["outbound_message_router"],
            )
            mock_response.assert_called_once_with({})

    async def test_introduction_start_x(self):
        self.mock_request.json = async_mock.CoroutineMock(
            return_value={
                "my_seed": "my_seed",
                "my_did": "my_did",
                "their_seed": "their_seed",
                "their_did": "their_did",
                "their_verkey": "their_verkey",
                "their_endpoint": "their_endpoint",
                "their_role": "their_role",
                "alias": "alias",
            }
        )
        self.mock_request.match_info = {"conn_id": "dummy"}
        self.mock_request.query = {
            "target_connection_id": "dummy",
            "message": "Hello",
        }
        mock_conn_rec = async_mock.MagicMock()
        mock_conn_rec.serialize = async_mock.MagicMock()

        with async_mock.patch.object(
            self.context, "inject", async_mock.CoroutineMock()
        ) as mock_ctx_inject:
            mock_ctx_inject.return_value = async_mock.MagicMock(
                start_introduction=async_mock.CoroutineMock(
                    side_effect=test_module.IntroductionError()
                )
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.introduction_start(self.mock_request)

    async def test_register(self):
        mock_app = async_mock.MagicMock()
        mock_app.add_routes = async_mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()

    async def test_post_process_routes(self):
        mock_app = async_mock.MagicMock(_state={"swagger_dict": {}})
        test_module.post_process_routes(mock_app)
        assert "tags" in mock_app._state["swagger_dict"]
