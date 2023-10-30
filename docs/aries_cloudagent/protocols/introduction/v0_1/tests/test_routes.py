from aries_cloudagent.tests import mock
from unittest import IsolatedAsyncioTestCase

from .....admin.request_context import AdminRequestContext

from .. import routes as test_module


class TestIntroductionRoutes(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.session_inject = {}
        self.context = AdminRequestContext.test_context(self.session_inject)
        self.request_dict = {
            "context": self.context,
            "outbound_message_router": mock.CoroutineMock(),
        }
        self.request = mock.MagicMock(
            app={},
            match_info={},
            query={},
            __getitem__=lambda _, k: self.request_dict[k],
        )

    async def test_introduction_start_no_service(self):
        self.request.json = mock.CoroutineMock(
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
        self.request.match_info = {"conn_id": "dummy"}
        self.request.query = {
            "target_connection_id": "dummy",
            "message": "Hello",
        }

        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.introduction_start(self.request)

    async def test_introduction_start(self):
        self.request.json = mock.CoroutineMock(
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
        self.request.match_info = {"conn_id": "dummy"}
        self.request.query = {
            "target_connection_id": "dummy",
            "message": "Hello",
        }
        mock_conn_rec = mock.MagicMock()
        mock_conn_rec.serialize = mock.MagicMock()

        with mock.patch.object(
            self.context, "inject_or", mock.MagicMock()
        ) as mock_ctx_inject, mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_ctx_inject.return_value = mock.MagicMock(
                start_introduction=mock.CoroutineMock()
            )

            await test_module.introduction_start(self.request)
            mock_ctx_inject.return_value.start_introduction.assert_called_once_with(
                self.request.match_info["conn_id"],
                self.request.query["target_connection_id"],
                self.request.query["message"],
                mock.ANY,
                self.request["outbound_message_router"],
            )
            mock_response.assert_called_once_with({})

    async def test_introduction_start_x(self):
        self.request.json = mock.CoroutineMock(
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
        self.request.match_info = {"conn_id": "dummy"}
        self.request.query = {
            "target_connection_id": "dummy",
            "message": "Hello",
        }
        mock_conn_rec = mock.MagicMock()
        mock_conn_rec.serialize = mock.MagicMock()

        with mock.patch.object(
            self.context, "inject_or", mock.MagicMock()
        ) as mock_ctx_inject:
            mock_ctx_inject.return_value = mock.MagicMock(
                start_introduction=mock.CoroutineMock(
                    side_effect=test_module.IntroductionError()
                )
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.introduction_start(self.request)

    async def test_register(self):
        mock_app = mock.MagicMock()
        mock_app.add_routes = mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()

    async def test_post_process_routes(self):
        mock_app = mock.MagicMock(_state={"swagger_dict": {}})
        test_module.post_process_routes(mock_app)
        assert "tags" in mock_app._state["swagger_dict"]
