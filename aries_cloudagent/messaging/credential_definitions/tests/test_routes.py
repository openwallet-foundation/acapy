from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from aiohttp import web as aio_web

from ....config.injection_context import InjectionContext
from ....issuer.base import BaseIssuer
from ....ledger.base import BaseLedger
from ....storage.base import BaseStorage
from ....messaging.request_context import RequestContext

from .. import routes as test_module


SCHEMA_ID = "WgWxqztrNooG92RXvxSTWv:2:schema_name:1.0"
CRED_DEF_ID = "WgWxqztrNooG92RXvxSTWv:3:CL:20:tag"


class TestCredentialDefinitionRoutes(AsyncTestCase):
    def setUp(self):
        self.context = InjectionContext(enforce_typing=False)

        self.ledger = async_mock.create_autospec(BaseLedger)
        self.ledger.__aenter__ = async_mock.CoroutineMock(return_value=self.ledger)
        self.ledger.create_and_send_credential_definition = async_mock.CoroutineMock(
            return_value=(CRED_DEF_ID, {"cred": "def"})
        )
        self.ledger.get_credential_definition = async_mock.CoroutineMock(
            return_value={"cred": "def"}
        )
        self.context.injector.bind_instance(BaseLedger, self.ledger)

        self.issuer = async_mock.create_autospec(BaseIssuer)
        self.context.injector.bind_instance(BaseIssuer, self.issuer)

        self.storage = async_mock.create_autospec(BaseStorage)
        self.storage.search_records = async_mock.MagicMock(
            return_value=async_mock.MagicMock(
                fetch_all=async_mock.CoroutineMock(
                    return_value=[async_mock.MagicMock(value=CRED_DEF_ID)]
                )
            )
        )
        self.context.injector.bind_instance(BaseStorage, self.storage)

        self.app = {
            "request_context": self.context,
        }

    async def test_send_credential_definition(self):
        mock_request = async_mock.MagicMock(
            app=self.app,
            json=async_mock.CoroutineMock(
                return_value={
                    "schema_id": "WgWxqztrNooG92RXvxSTWv:2:schema_name:1.0",
                    "support_revocation": False,
                    "tag": "tag",
                }
            ),
        )

        with async_mock.patch.object(test_module.web, "json_response") as mock_response:
            result = await test_module.credential_definitions_send_credential_definition(
                mock_request
            )
            assert result == mock_response.return_value
            mock_response.assert_called_once_with(
                {"credential_definition_id": CRED_DEF_ID}
            )

    async def test_created(self):
        mock_request = async_mock.MagicMock(
            app=self.app,
            json=async_mock.CoroutineMock(
                return_value={
                    "schema_id": "WgWxqztrNooG92RXvxSTWv:2:schema_name:1.0",
                    "support_revocation": False,
                    "tag": "tag",
                }
            ),
            match_info={"cred_def_id": CRED_DEF_ID},
        )

        with async_mock.patch.object(test_module.web, "json_response") as mock_response:
            result = await test_module.credential_definitions_created(mock_request)
            assert result == mock_response.return_value
            mock_response.assert_called_once_with(
                {"credential_definition_ids": [CRED_DEF_ID]}
            )

    async def test_get_credential_definition(self):
        mock_request = async_mock.MagicMock(
            app=self.app,
            json=async_mock.CoroutineMock(
                return_value={
                    "schema_id": "WgWxqztrNooG92RXvxSTWv:2:schema_name:1.0",
                    "support_revocation": False,
                    "tag": "tag",
                }
            ),
            match_info={"cred_def_id": CRED_DEF_ID},
        )

        with async_mock.patch.object(test_module.web, "json_response") as mock_response:
            result = await test_module.credential_definitions_get_credential_definition(
                mock_request
            )
            assert result == mock_response.return_value
            mock_response.assert_called_once_with(
                {"credential_definition": {"cred": "def"}}
            )

    async def test_register(self):
        mock_app = async_mock.MagicMock()
        mock_app.add_routes = async_mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()
