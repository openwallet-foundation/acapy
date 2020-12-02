from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from ....admin.request_context import AdminRequestContext
from ....indy.issuer import IndyIssuer
from ....ledger.base import BaseLedger
from ....storage.base import BaseStorage

from .. import routes as test_module


SCHEMA_ID = "WgWxqztrNooG92RXvxSTWv:2:schema_name:1.0"


class TestSchemaRoutes(AsyncTestCase):
    def setUp(self):
        self.session_inject = {}
        self.context = AdminRequestContext.test_context(self.session_inject)
        self.request_dict = {"context": self.context}
        self.request = async_mock.MagicMock(
            app={"outbound_message_router": async_mock.CoroutineMock()},
            match_info={},
            query={},
            __getitem__=lambda _, k: self.request_dict[k],
        )

        self.ledger = async_mock.create_autospec(BaseLedger)
        self.ledger.__aenter__ = async_mock.CoroutineMock(return_value=self.ledger)
        self.ledger.create_and_send_schema = async_mock.CoroutineMock(
            return_value=(SCHEMA_ID, {"schema": "def"})
        )
        self.ledger.get_schema = async_mock.CoroutineMock(
            return_value={"schema": "def"}
        )
        self.session_inject[BaseLedger] = self.ledger

        self.issuer = async_mock.create_autospec(IndyIssuer)
        self.session_inject[IndyIssuer] = self.issuer

        self.storage = async_mock.create_autospec(BaseStorage)
        self.storage.search_records = async_mock.MagicMock(
            return_value=async_mock.MagicMock(
                fetch_all=async_mock.CoroutineMock(
                    return_value=[async_mock.MagicMock(value=SCHEMA_ID)]
                )
            )
        )
        self.session_inject[BaseStorage] = self.storage

    async def test_send_schema(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "schema_name": "schema_name",
                "schema_version": "1.0",
                "attributes": ["table", "drink", "colour"],
            }
        )

        with async_mock.patch.object(test_module.web, "json_response") as mock_response:
            result = await test_module.schemas_send_schema(self.request)
            assert result == mock_response.return_value
            mock_response.assert_called_once_with(
                {"schema_id": SCHEMA_ID, "schema": {"schema": "def"}}
            )

    async def test_send_schema_no_ledger(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "schema_name": "schema_name",
                "schema_version": "1.0",
                "attributes": ["table", "drink", "colour"],
            }
        )

        self.session_inject[BaseLedger] = None
        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.schemas_send_schema(self.request)

    async def test_send_schema_x_ledger(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "schema_name": "schema_name",
                "schema_version": "1.0",
                "attributes": ["table", "drink", "colour"],
            }
        )
        self.ledger.create_and_send_schema = async_mock.CoroutineMock(
            side_effect=test_module.LedgerError("Down for routine maintenance")
        )

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.schemas_send_schema(self.request)

    async def test_created(self):
        self.request.match_info = {"schema_id": SCHEMA_ID}

        with async_mock.patch.object(test_module.web, "json_response") as mock_response:
            result = await test_module.schemas_created(self.request)
            assert result == mock_response.return_value
            mock_response.assert_called_once_with({"schema_ids": [SCHEMA_ID]})

    async def test_get_schema(self):
        self.request.match_info = {"schema_id": SCHEMA_ID}

        with async_mock.patch.object(test_module.web, "json_response") as mock_response:
            result = await test_module.schemas_get_schema(self.request)
            assert result == mock_response.return_value
            mock_response.assert_called_once_with({"schema": {"schema": "def"}})

    async def test_get_schema_on_seq_no(self):
        self.request.match_info = {"schema_id": "12345"}

        with async_mock.patch.object(test_module.web, "json_response") as mock_response:
            result = await test_module.schemas_get_schema(self.request)
            assert result == mock_response.return_value
            mock_response.assert_called_once_with({"schema": {"schema": "def"}})

    async def test_get_schema_no_ledger(self):
        self.request.match_info = {"schema_id": SCHEMA_ID}
        self.ledger.get_schema = async_mock.CoroutineMock(
            side_effect=test_module.LedgerError("Down for routine maintenance")
        )

        self.session_inject[BaseLedger] = None
        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.schemas_get_schema(self.request)

    async def test_get_schema_x_ledger(self):
        self.request.match_info = {"schema_id": SCHEMA_ID}
        self.ledger.get_schema = async_mock.CoroutineMock(
            side_effect=test_module.LedgerError("Down for routine maintenance")
        )

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.schemas_get_schema(self.request)

    async def test_register(self):
        mock_app = async_mock.MagicMock()
        mock_app.add_routes = async_mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()

    async def test_post_process_routes(self):
        mock_app = async_mock.MagicMock(_state={"swagger_dict": {}})
        test_module.post_process_routes(mock_app)
        assert "tags" in mock_app._state["swagger_dict"]
