from unittest import IsolatedAsyncioTestCase

from .....admin.request_context import AdminRequestContext
from .....storage.error import StorageError
from .....tests import mock
from .....utils.testing import create_test_profile
from .. import routes as test_module
from ..manager import V20DiscoveryMgr
from ..messages.queries import Queries, QueryItem
from ..models.discovery_record import V20DiscoveryExchangeRecord


class TestDiscoveryRoutes(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.session_inject = {}
        self.profile = await create_test_profile(
            settings={
                "admin.admin_api_key": "secret-key",
            }
        )
        self.context = AdminRequestContext.test_context(self.session_inject, self.profile)
        self.request_dict = {
            "context": self.context,
            "outbound_message_router": mock.CoroutineMock(),
        }
        self.request = mock.MagicMock(
            app={},
            match_info={},
            query={},
            __getitem__=lambda _, k: self.request_dict[k],
            headers={"x-api-key": "secret-key"},
        )

    async def test_query_features(self):
        self.request.json = mock.CoroutineMock()

        self.request.query = {"query_protocol": "*"}

        test_rec = V20DiscoveryExchangeRecord(
            discovery_exchange_id="3fa85f64-5717-4562-b3fc-2c963f66afa6",
            queries_msg=Queries(
                queries=[
                    QueryItem(feature_type="protocol", match="*"),
                    QueryItem(feature_type="goal-code", match="test"),
                ]
            ),
        )

        with (
            mock.patch.object(test_module.web, "json_response") as mock_response,
            mock.patch.object(
                V20DiscoveryMgr, "create_and_send_query", autospec=True
            ) as mock_create_query,
        ):
            mock_create_query.return_value = test_rec
            await test_module.query_features(self.request)
            mock_response.assert_called_once_with(test_rec.serialize())

    async def test_query_features_with_connection(self):
        self.request.json = mock.CoroutineMock()

        self.request.query = {
            "query_protocol": "*",
            "connection_id": "test",
            "query_goal_code": "test",
        }

        test_rec = V20DiscoveryExchangeRecord(
            discovery_exchange_id="3fa85f64-5717-4562-b3fc-2c963f66afa6",
            queries_msg=Queries(
                queries=[
                    QueryItem(feature_type="protocol", match="*"),
                    QueryItem(feature_type="goal-code", match="test"),
                ]
            ),
        )

        with (
            mock.patch.object(test_module.web, "json_response") as mock_response,
            mock.patch.object(
                V20DiscoveryMgr, "create_and_send_query", autospec=True
            ) as mock_create_query,
        ):
            mock_create_query.return_value = test_rec
            await test_module.query_features(self.request)
            mock_response.assert_called_once_with(test_rec.serialize())

    async def test_query_records(self):
        self.request.json = mock.CoroutineMock()

        self.request.query = {"connection_id": "test"}

        test_rec = V20DiscoveryExchangeRecord(
            discovery_exchange_id="3fa85f64-5717-4562-b3fc-2c963f66afa6",
            queries_msg=Queries(
                queries=[
                    QueryItem(feature_type="protocol", match="*"),
                    QueryItem(feature_type="goal-code", match="test"),
                ]
            ),
        )

        with (
            mock.patch.object(test_module.web, "json_response") as mock_response,
            mock.patch.object(
                test_module, "V20DiscoveryExchangeRecord", autospec=True
            ) as mock_ex_rec,
        ):
            mock_ex_rec.retrieve_by_connection_id.return_value = test_rec
            await test_module.query_records(self.request)
            mock_response.assert_called_once_with({"results": [test_rec.serialize()]})

    async def test_query_records_x(self):
        self.request.json = mock.CoroutineMock()

        self.request.query = {"connection_id": "test"}

        with (
            mock.patch.object(test_module.web, "json_response"),
            mock.patch.object(
                test_module, "V20DiscoveryExchangeRecord", autospec=True
            ) as mock_ex_rec,
        ):
            mock_ex_rec.retrieve_by_connection_id.side_effect = StorageError
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.query_records(self.request)

    async def test_query_records_all(self):
        self.request.json = mock.CoroutineMock()

        test_recs = [
            V20DiscoveryExchangeRecord(
                discovery_exchange_id="3fa85f64-5717-4562-b3fc-2c963f66afa6",
                queries_msg=Queries(
                    queries=[
                        QueryItem(feature_type="protocol", match="*"),
                        QueryItem(feature_type="goal-code", match="test"),
                    ]
                ),
            ),
            V20DiscoveryExchangeRecord(
                discovery_exchange_id="3fa85f64-5717-4562-b3fc-2c963f66afa7",
                queries_msg=Queries(
                    queries=[
                        QueryItem(feature_type="protocol", match="test"),
                        QueryItem(feature_type="goal-code", match="*"),
                    ]
                ),
            ),
        ]

        with (
            mock.patch.object(test_module.web, "json_response") as mock_response,
            mock.patch.object(
                test_module, "V20DiscoveryExchangeRecord", autospec=True
            ) as mock_ex_rec,
        ):
            mock_ex_rec.query.return_value = test_recs
            await test_module.query_records(self.request)
            mock_response.assert_called_once_with(
                {"results": [k.serialize() for k in test_recs]}
            )

    async def test_query_records_connection_x(self):
        self.request.json = mock.CoroutineMock()

        with (
            mock.patch.object(test_module.web, "json_response"),
            mock.patch.object(
                test_module, "V20DiscoveryExchangeRecord", autospec=True
            ) as mock_ex_rec,
        ):
            mock_ex_rec.query.side_effect = StorageError
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.query_records(self.request)

    async def test_register(self):
        mock_app = mock.MagicMock()
        mock_app.add_routes = mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()

    async def test_post_process_routes(self):
        mock_app = mock.MagicMock(_state={"swagger_dict": {}})
        test_module.post_process_routes(mock_app)
        assert "tags" in mock_app._state["swagger_dict"]
