import json
from unittest import IsolatedAsyncioTestCase

from aries_askar import AskarErrorCode

from ...admin.request_context import AdminRequestContext
from ...anoncreds.holder import AnonCredsHolder, AnonCredsHolderError
from ...indy.holder import IndyHolder
from ...ledger.base import BaseLedger
from ...storage.vc_holder.base import VCHolder
from ...storage.vc_holder.vc_record import VCRecord
from ...tests import mock
from ...utils.testing import create_test_profile
from .. import routes as test_module

VC_RECORD = VCRecord(
    contexts=[
        "https://www.w3.org/2018/credentials/v1",
        "https://www.w3.org/2018/credentials/examples/v1",
    ],
    expanded_types=[
        "https://www.w3.org/2018/credentials#VerifiableCredential",
        "https://example.org/examples#UniversityDegreeCredential",
    ],
    issuer_id="https://example.edu/issuers/565049",
    subject_ids=["did:example:ebfeb1f712ebc6f1c276e12ec21"],
    proof_types=["Ed25519Signature2018"],
    schema_ids=["https://example.org/examples/degree.json"],
    cred_value={"...": "..."},
    given_id="http://example.edu/credentials/3732",
    cred_tags={"some": "tag"},
)


class TestHolderRoutes(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.profile = await create_test_profile(
            settings={
                "admin.admin_api_key": "secret-key",
            }
        )
        self.context = self.profile.context
        setattr(self.context, "profile", self.profile)

        self.request_dict = {"context": self.context}
        self.request = mock.MagicMock(
            app={},
            match_info={},
            query={},
            __getitem__=lambda _, k: self.request_dict[k],
            headers={"x-api-key": "secret-key"},
        )
        self.profile.context.injector.bind_instance(
            IndyHolder, mock.MagicMock(IndyHolder, autospec=True)
        )

    async def test_credentials_get(self):
        self.request.match_info = {"credential_id": "dummy"}
        mock_holder = mock.MagicMock(IndyHolder, autospec=True)
        mock_holder.get_credential = mock.CoroutineMock(
            return_value=json.dumps({"hello": "world"})
        )
        self.profile.context.injector.bind_instance(
            IndyHolder,
            mock_holder,
        )

        with mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as json_response:
            result = await test_module.credentials_get(self.request)
            json_response.assert_called_once_with({"hello": "world"})
            assert result is json_response.return_value

    @mock.patch.object(AnonCredsHolder, "get_credential")
    async def test_credentials_get_with_anoncreds(self, mock_get_credential):
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
            match_info={"credential_id": "dummy"},
            __getitem__=lambda _, k: self.request_dict[k],
            context=self.context,
            headers={"x-api-key": "secret-key"},
        )
        self.context.inject = mock.Mock(
            return_value=mock.MagicMock(
                get_credential=mock.CoroutineMock(return_value="test-credential")
            )
        )

        mock_get_credential.return_value = json.dumps({"hello": "world"})

        with mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as json_response:
            result = await test_module.credentials_get(self.request)
            json_response.assert_called_once_with({"hello": "world"})
            assert result is json_response.return_value
            assert mock_get_credential.called

    async def test_credentials_get_not_found(self):
        self.request.match_info = {"credential_id": "dummy"}
        mock_holder = mock.MagicMock(IndyHolder, autospec=True)
        mock_holder.get_credential = mock.CoroutineMock(
            side_effect=test_module.WalletNotFoundError()
        )
        self.profile.context.injector.bind_instance(IndyHolder, mock_holder)

        with self.assertRaises(test_module.web.HTTPNotFound):
            await test_module.credentials_get(self.request)

    async def test_credentials_revoked(self):
        self.request.match_info = {"credential_id": "dummy"}
        self.profile.context.injector.bind_instance(
            BaseLedger, mock.create_autospec(BaseLedger)
        )
        mock_holder = mock.MagicMock(IndyHolder, autospec=True)
        mock_holder.credential_revoked = mock.CoroutineMock(return_value=False)
        self.profile.context.injector.bind_instance(IndyHolder, mock_holder)

        with mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as json_response:
            result = await test_module.credentials_revoked(self.request)
            json_response.assert_called_once_with({"revoked": False})
            assert result is json_response.return_value

    @mock.patch.object(AnonCredsHolder, "credential_revoked")
    async def test_credentials_revoked_with_anoncreds(self, mock_credential_revoked):
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
            match_info={"credential_id": "dummy"},
            __getitem__=lambda _, k: self.request_dict[k],
            context=self.context,
            headers={"x-api-key": "secret-key"},
        )
        self.context.inject = mock.Mock(
            return_value=mock.MagicMock(
                get_credential=mock.CoroutineMock(return_value="test-credential")
            )
        )

        mock_credential_revoked.return_value = False

        with mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as json_response:
            result = await test_module.credentials_revoked(self.request)
            json_response.assert_called_once_with({"revoked": False})
            assert result is json_response.return_value

    async def test_credentials_revoked_no_ledger(self):
        self.request.match_info = {"credential_id": "dummy"}

        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.credentials_revoked(self.request)

    async def test_credentials_not_found(self):
        self.request.match_info = {"credential_id": "dummy"}
        self.profile.context.injector.bind_instance(
            BaseLedger, mock.create_autospec(BaseLedger)
        )

        mock_holder = mock.MagicMock(IndyHolder, autospec=True)
        mock_holder.credential_revoked = mock.CoroutineMock(
            side_effect=test_module.WalletNotFoundError("no such cred")
        )
        self.profile.context.injector.bind_instance(IndyHolder, mock_holder)

        with self.assertRaises(test_module.web.HTTPNotFound):
            await test_module.credentials_revoked(self.request)

    async def test_credentials_x_ledger(self):
        self.request.match_info = {"credential_id": "dummy"}
        self.profile.context.injector.bind_instance(
            BaseLedger, mock.create_autospec(BaseLedger)
        )
        mock_holder = mock.MagicMock(IndyHolder, autospec=True)
        mock_holder.credential_revoked = mock.CoroutineMock(
            side_effect=test_module.LedgerError("down for maintenance")
        )
        self.profile.context.injector.bind_instance(IndyHolder, mock_holder)

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.credentials_revoked(self.request)

    async def test_attribute_mime_types_get(self):
        self.request.match_info = {"credential_id": "dummy"}
        mock_holder = mock.MagicMock(IndyHolder, autospec=True)
        mock_holder.get_mime_type = mock.CoroutineMock(
            side_effect=[None, {"a": "application/jpeg"}]
        )
        self.profile.context.injector.bind_instance(IndyHolder, mock_holder)

        with mock.patch.object(test_module.web, "json_response") as mock_response:
            await test_module.credentials_attr_mime_types_get(self.request)
            mock_response.assert_called_once_with({"results": None})

        with mock.patch.object(test_module.web, "json_response") as mock_response:
            await test_module.credentials_attr_mime_types_get(self.request)
            mock_response.assert_called_once_with({"results": {"a": "application/jpeg"}})

    @mock.patch.object(AnonCredsHolder, "get_mime_type")
    async def test_attribute_mime_types_get_with_anoncreds(self, mock_get_mime_type):
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
            match_info={"credential_id": "dummy"},
            __getitem__=lambda _, k: self.request_dict[k],
            context=self.context,
            headers={"x-api-key": "secret-key"},
        )
        self.context.inject = mock.Mock(
            return_value=mock.MagicMock(
                get_credential=mock.CoroutineMock(return_value="test-credential")
            )
        )

        mock_get_mime_type.side_effect = [None, {"a": "application/jpeg"}]

        with mock.patch.object(test_module.web, "json_response") as mock_response:
            await test_module.credentials_attr_mime_types_get(self.request)
            mock_response.assert_called_once_with({"results": None})

        with mock.patch.object(test_module.web, "json_response") as mock_response:
            await test_module.credentials_attr_mime_types_get(self.request)
            mock_response.assert_called_once_with({"results": {"a": "application/jpeg"}})
            assert mock_get_mime_type.called

    async def test_credentials_remove(self):
        self.request.match_info = {"credential_id": "dummy"}
        mock_holder = mock.MagicMock(IndyHolder, autospec=True)
        mock_holder.delete_credential = mock.CoroutineMock(return_value=None)
        self.profile.context.injector.bind_instance(IndyHolder, mock_holder)

        with mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as json_response:
            result = await test_module.credentials_remove(self.request)
            json_response.assert_called_once_with({})
            assert result is json_response.return_value

    @mock.patch.object(AnonCredsHolder, "delete_credential")
    async def test_credentials_remove_with_anoncreds(self, mock_delete_credential):
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
            match_info={"credential_id": "dummy"},
            __getitem__=lambda _, k: self.request_dict[k],
            context=self.context,
            headers={"x-api-key": "secret-key"},
        )
        self.context.inject = mock.Mock(
            return_value=mock.MagicMock(
                get_credential=mock.CoroutineMock(return_value="test-credential")
            )
        )

        # Anoncreds holder errors
        mock_delete_credential.side_effect = [
            None,
            AnonCredsHolderError("anoncreds error", error_code=AskarErrorCode.NOT_FOUND),
            AnonCredsHolderError("anoncreds error", error_code=AskarErrorCode.UNEXPECTED),
            AnonCredsHolderError("anoncreds error", error_code=AskarErrorCode.NOT_FOUND),
        ]

        # Indy holder errors
        mock_indy_holder = mock.MagicMock(IndyHolder, autospec=True)
        mock_indy_holder.delete_credential.side_effect = [
            test_module.WalletNotFoundError(),  # Indy not found after anoncreds not found
            None,  # Indy found after second anoncreds not found side effect
        ]
        self.profile.context.injector.bind_instance(IndyHolder, mock_indy_holder)

        with mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as json_response:
            # First mock delete has no side effect; delete succeeds
            result = await test_module.credentials_remove(self.request)
            json_response.assert_called_once_with({})
            assert result is json_response.return_value
            assert mock_delete_credential.called

            # Not found after anoncreds not found and indy not found
            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.credentials_remove(self.request)

            # Bad request after anoncreds unexpected error
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credentials_remove(self.request)

            # Indy found after anoncreds not found
            result = await test_module.credentials_remove(self.request)
            assert result is json_response.return_value

    async def test_credentials_remove_not_found(self):
        self.request.match_info = {"credential_id": "dummy"}
        mock_holder = mock.MagicMock(IndyHolder, autospec=True)
        mock_holder.delete_credential = mock.CoroutineMock(
            side_effect=test_module.WalletNotFoundError()
        )
        self.profile.context.injector.bind_instance(IndyHolder, mock_holder)

        with self.assertRaises(test_module.web.HTTPNotFound):
            await test_module.credentials_remove(self.request)

    async def test_credentials_list(self):
        self.request.query = {"start": "0", "count": "10"}
        mock_holder = mock.MagicMock(IndyHolder, autospec=True)
        mock_holder.get_credentials = mock.CoroutineMock(
            return_value=[{"hello": "world"}]
        )
        self.profile.context.injector.bind_instance(IndyHolder, mock_holder)

        with mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as json_response:
            result = await test_module.credentials_list(self.request)
            json_response.assert_called_once_with({"results": [{"hello": "world"}]})
            assert result is json_response.return_value

    @mock.patch.object(AnonCredsHolder, "get_credentials")
    async def test_credentials_list_with_anoncreds(self, mock_get_credentials):
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
            match_info={"credential_id": "dummy"},
            query={
                "start": "0",
                "count": "10",
            },
            __getitem__=lambda _, k: self.request_dict[k],
            context=self.context,
            headers={"x-api-key": "secret-key"},
        )
        self.context.inject = mock.Mock(
            return_value=mock.MagicMock(
                get_credential=mock.CoroutineMock(return_value="test-credential")
            )
        )

        mock_get_credentials.return_value = [{"hello": "world"}]

        with mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as json_response:
            result = await test_module.credentials_list(self.request)
            json_response.assert_called_once_with({"results": [{"hello": "world"}]})
            assert result is json_response.return_value

    async def test_credentials_list_x_holder(self):
        self.request.query = {"start": "0", "count": "10"}
        mock_holder = mock.MagicMock(IndyHolder, autospec=True)
        mock_holder.get_credentials = mock.CoroutineMock(
            side_effect=test_module.IndyHolderError()
        )
        self.profile.context.injector.bind_instance(IndyHolder, mock_holder)

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.credentials_list(self.request)

    async def test_w3c_cred_get(self):
        self.request.match_info = {"credential_id": "dummy"}
        mock_holder = mock.MagicMock(VCHolder, autospec=True)
        mock_holder.retrieve_credential_by_id = mock.CoroutineMock(return_value=VC_RECORD)
        self.profile.context.injector.bind_instance(VCHolder, mock_holder)

        with mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as json_response:
            await test_module.w3c_cred_get(self.request)
            json_response.assert_called_once_with(VC_RECORD.serialize())

    async def test_w3c_cred_get_not_found_x(self):
        self.request.match_info = {"credential_id": "dummy"}
        mock_holder = mock.MagicMock(VCHolder, autospec=True)
        mock_holder.retrieve_credential_by_id = mock.CoroutineMock(
            side_effect=test_module.StorageNotFoundError()
        )
        self.profile.context.injector.bind_instance(VCHolder, mock_holder)

        with self.assertRaises(test_module.web.HTTPNotFound):
            await test_module.w3c_cred_get(self.request)

    async def test_w3c_cred_get_storage_x(self):
        self.request.match_info = {"credential_id": "dummy"}
        mock_holder = mock.MagicMock(VCHolder, autospec=True)
        mock_holder.retrieve_credential_by_id = mock.CoroutineMock(
            side_effect=test_module.StorageError()
        )
        self.profile.context.injector.bind_instance(VCHolder, mock_holder)

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.w3c_cred_get(self.request)

    async def test_w3c_cred_remove(self):
        self.request.match_info = {"credential_id": "dummy"}
        mock_holder = mock.MagicMock(VCHolder, autospec=True)
        mock_holder.retrieve_credential_by_id = mock.CoroutineMock(return_value=VC_RECORD)
        mock_holder.delete_credential = mock.CoroutineMock(return_value=None)
        self.profile.context.injector.bind_instance(VCHolder, mock_holder)

        with mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as json_response:
            result = await test_module.w3c_cred_remove(self.request)
            json_response.assert_called_once_with({})
            assert result is json_response.return_value

    async def test_w3c_cred_remove_not_found_x(self):
        self.request.match_info = {"credential_id": "dummy"}
        mock_holder = mock.MagicMock(VCHolder, autospec=True)
        mock_holder.retrieve_credential_by_id = mock.CoroutineMock(
            side_effect=test_module.StorageNotFoundError()
        )
        self.profile.context.injector.bind_instance(VCHolder, mock_holder)

        with self.assertRaises(test_module.web.HTTPNotFound):
            await test_module.w3c_cred_remove(self.request)

    async def test_w3c_cred_remove_storage_x(self):
        self.request.match_info = {"credential_id": "dummy"}
        mock_holder = mock.MagicMock(VCHolder, autospec=True)
        mock_holder.retrieve_credential_by_id = mock.CoroutineMock(return_value=VC_RECORD)
        mock_holder.delete_credential = mock.CoroutineMock(
            side_effect=test_module.StorageError()
        )
        self.profile.context.injector.bind_instance(VCHolder, mock_holder)

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.w3c_cred_remove(self.request)

    async def test_w3c_creds_list(self):
        self.request.json = mock.CoroutineMock(
            return_value={
                "types": [
                    "VerifiableCredential",
                    "AlumniCredential",
                ],
                "issuer_id": "https://example.edu/issuers/565049",
                "subject_id": "did:example:ebfeb1f712ebc6f1c276e12ec21",
                "max_results": "1",
            }
        )
        mock_holder = mock.MagicMock(VCHolder, autospec=True)
        mock_holder.search_credentials = mock.MagicMock(
            return_value=mock.MagicMock(
                fetch=mock.CoroutineMock(return_value=[VC_RECORD])
            )
        )
        self.profile.context.injector.bind_instance(VCHolder, mock_holder)

        with mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as json_response:
            await test_module.w3c_creds_list(self.request)
            json_response.assert_called_once_with({"results": [VC_RECORD.serialize()]})

    async def test_w3c_creds_list_not_found_x(self):
        self.request.json = mock.CoroutineMock(
            return_value={
                "types": [
                    "VerifiableCredential",
                    "AlumniCredential",
                ],
                "issuer_id": "https://example.edu/issuers/565049",
                "subject_id": "did:example:ebfeb1f712ebc6f1c276e12ec21",
                "max_results": "1",
            }
        )
        mock_holder = mock.MagicMock(VCHolder, autospec=True)
        mock_holder.search_credentials = mock.MagicMock(
            return_value=mock.MagicMock(
                fetch=mock.CoroutineMock(side_effect=test_module.StorageNotFoundError())
            )
        )
        self.profile.context.injector.bind_instance(VCHolder, mock_holder)

        with self.assertRaises(test_module.web.HTTPNotFound):
            await test_module.w3c_creds_list(self.request)

    async def test_w3c_creds_list_storage_x(self):
        self.request.json = mock.CoroutineMock(
            return_value={
                "types": [
                    "VerifiableCredential",
                    "AlumniCredential",
                ],
                "issuer_id": "https://example.edu/issuers/565049",
                "subject_id": "did:example:ebfeb1f712ebc6f1c276e12ec21",
                "max_results": "1",
            }
        )
        mock_holder = mock.MagicMock(VCHolder, autospec=True)
        mock_holder.search_credentials = mock.MagicMock(
            return_value=mock.MagicMock(
                fetch=mock.CoroutineMock(side_effect=test_module.StorageError())
            )
        )
        self.profile.context.injector.bind_instance(VCHolder, mock_holder)

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.w3c_creds_list(self.request)

    async def test_register(self):
        mock_app = mock.MagicMock()
        mock_app.add_routes = mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()

    async def test_post_process_routes(self):
        mock_app = mock.MagicMock(_state={"swagger_dict": {}})
        test_module.post_process_routes(mock_app)
        assert "tags" in mock_app._state["swagger_dict"]
