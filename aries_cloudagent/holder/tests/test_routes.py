import json

from aries_cloudagent.tests import mock
from unittest import IsolatedAsyncioTestCase

from ...core.in_memory import InMemoryProfile
from ...ledger.base import BaseLedger

from ...indy.holder import IndyHolder
from ...storage.vc_holder.base import VCHolder
from ...storage.vc_holder.vc_record import VCRecord

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
    def setUp(self):
        self.profile = InMemoryProfile.test_profile()
        self.context = self.profile.context
        setattr(self.context, "profile", self.profile)

        self.request_dict = {"context": self.context}
        self.request = mock.MagicMock(
            app={},
            match_info={},
            query={},
            __getitem__=lambda _, k: self.request_dict[k],
        )

    async def test_credentials_get(self):
        self.request.match_info = {"credential_id": "dummy"}
        self.profile.context.injector.bind_instance(
            IndyHolder,
            mock.MagicMock(
                get_credential=mock.CoroutineMock(
                    return_value=json.dumps({"hello": "world"})
                )
            ),
        )

        with mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as json_response:
            result = await test_module.credentials_get(self.request)
            json_response.assert_called_once_with({"hello": "world"})
            assert result is json_response.return_value

    async def test_credentials_get_not_found(self):
        self.request.match_info = {"credential_id": "dummy"}
        self.profile.context.injector.bind_instance(
            IndyHolder,
            mock.MagicMock(
                get_credential=mock.CoroutineMock(
                    side_effect=test_module.WalletNotFoundError()
                )
            ),
        )

        with self.assertRaises(test_module.web.HTTPNotFound):
            await test_module.credentials_get(self.request)

    async def test_credentials_revoked(self):
        self.request.match_info = {"credential_id": "dummy"}
        self.profile.context.injector.bind_instance(
            BaseLedger, mock.create_autospec(BaseLedger)
        )
        self.profile.context.injector.bind_instance(
            IndyHolder,
            mock.MagicMock(credential_revoked=mock.CoroutineMock(return_value=False)),
        )

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
        self.profile.context.injector.bind_instance(
            IndyHolder,
            mock.MagicMock(
                credential_revoked=mock.CoroutineMock(
                    side_effect=test_module.WalletNotFoundError("no such cred")
                )
            ),
        )

        with self.assertRaises(test_module.web.HTTPNotFound):
            await test_module.credentials_revoked(self.request)

    async def test_credentials_x_ledger(self):
        self.request.match_info = {"credential_id": "dummy"}
        ledger = mock.create_autospec(BaseLedger)
        self.profile.context.injector.bind_instance(
            BaseLedger, mock.create_autospec(BaseLedger)
        )
        self.profile.context.injector.bind_instance(
            IndyHolder,
            mock.MagicMock(
                credential_revoked=mock.CoroutineMock(
                    side_effect=test_module.LedgerError("down for maintenance")
                )
            ),
        )

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.credentials_revoked(self.request)

    async def test_attribute_mime_types_get(self):
        self.request.match_info = {"credential_id": "dummy"}
        self.profile.context.injector.bind_instance(
            IndyHolder,
            mock.MagicMock(
                get_mime_type=mock.CoroutineMock(
                    side_effect=[None, {"a": "application/jpeg"}]
                )
            ),
        )

        with mock.patch.object(test_module.web, "json_response") as mock_response:
            await test_module.credentials_attr_mime_types_get(self.request)
            mock_response.assert_called_once_with({"results": None})

        with mock.patch.object(test_module.web, "json_response") as mock_response:
            await test_module.credentials_attr_mime_types_get(self.request)
            mock_response.assert_called_once_with(
                {"results": {"a": "application/jpeg"}}
            )

    async def test_credentials_remove(self):
        self.request.match_info = {"credential_id": "dummy"}
        self.profile.context.injector.bind_instance(
            IndyHolder,
            mock.MagicMock(delete_credential=mock.CoroutineMock(return_value=None)),
        )

        with mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as json_response:
            result = await test_module.credentials_remove(self.request)
            json_response.assert_called_once_with({})
            assert result is json_response.return_value

    async def test_credentials_remove_not_found(self):
        self.request.match_info = {"credential_id": "dummy"}
        self.profile.context.injector.bind_instance(
            IndyHolder,
            mock.MagicMock(
                delete_credential=mock.CoroutineMock(
                    side_effect=test_module.WalletNotFoundError()
                )
            ),
        )
        with self.assertRaises(test_module.web.HTTPNotFound):
            await test_module.credentials_remove(self.request)

    async def test_credentials_list(self):
        self.request.query = {"start": "0", "count": "10"}
        self.profile.context.injector.bind_instance(
            IndyHolder,
            mock.MagicMock(
                get_credentials=mock.CoroutineMock(return_value=[{"hello": "world"}])
            ),
        )

        with mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as json_response:
            result = await test_module.credentials_list(self.request)
            json_response.assert_called_once_with({"results": [{"hello": "world"}]})
            assert result is json_response.return_value

    async def test_credentials_list_x_holder(self):
        self.request.query = {"start": "0", "count": "10"}
        self.profile.context.injector.bind_instance(
            IndyHolder,
            mock.MagicMock(
                get_credentials=mock.CoroutineMock(
                    side_effect=test_module.IndyHolderError()
                )
            ),
        )

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.credentials_list(self.request)

    async def test_w3c_cred_get(self):
        self.request.match_info = {"credential_id": "dummy"}
        self.profile.context.injector.bind_instance(
            VCHolder,
            mock.MagicMock(
                retrieve_credential_by_id=mock.CoroutineMock(return_value=VC_RECORD)
            ),
        )

        with mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as json_response:
            result = await test_module.w3c_cred_get(self.request)
            json_response.assert_called_once_with(VC_RECORD.serialize())

    async def test_w3c_cred_get_not_found_x(self):
        self.request.match_info = {"credential_id": "dummy"}
        self.profile.context.injector.bind_instance(
            VCHolder,
            mock.MagicMock(
                retrieve_credential_by_id=mock.CoroutineMock(
                    side_effect=test_module.StorageNotFoundError()
                )
            ),
        )

        with self.assertRaises(test_module.web.HTTPNotFound):
            await test_module.w3c_cred_get(self.request)

    async def test_w3c_cred_get_storage_x(self):
        self.request.match_info = {"credential_id": "dummy"}
        self.profile.context.injector.bind_instance(
            VCHolder,
            mock.MagicMock(
                retrieve_credential_by_id=mock.CoroutineMock(
                    side_effect=test_module.StorageError()
                )
            ),
        )

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.w3c_cred_get(self.request)

    async def test_w3c_cred_remove(self):
        self.request.match_info = {"credential_id": "dummy"}
        self.profile.context.injector.bind_instance(
            VCHolder,
            mock.MagicMock(
                retrieve_credential_by_id=mock.CoroutineMock(return_value=VC_RECORD),
                delete_credential=mock.CoroutineMock(return_value=None),
            ),
        )

        with mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as json_response:
            result = await test_module.w3c_cred_remove(self.request)
            json_response.assert_called_once_with({})
            assert result is json_response.return_value

    async def test_w3c_cred_remove_not_found_x(self):
        self.request.match_info = {"credential_id": "dummy"}
        self.profile.context.injector.bind_instance(
            VCHolder,
            mock.MagicMock(
                retrieve_credential_by_id=mock.CoroutineMock(
                    side_effect=test_module.StorageNotFoundError()
                )
            ),
        )

        with self.assertRaises(test_module.web.HTTPNotFound):
            await test_module.w3c_cred_remove(self.request)

    async def test_w3c_cred_remove_storage_x(self):
        self.request.match_info = {"credential_id": "dummy"}
        self.profile.context.injector.bind_instance(
            VCHolder,
            mock.MagicMock(
                retrieve_credential_by_id=mock.CoroutineMock(return_value=VC_RECORD),
                delete_credential=mock.CoroutineMock(
                    side_effect=test_module.StorageError()
                ),
            ),
        )

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
        self.profile.context.injector.bind_instance(
            VCHolder,
            mock.MagicMock(
                search_credentials=mock.MagicMock(
                    return_value=mock.MagicMock(
                        fetch=mock.CoroutineMock(return_value=[VC_RECORD])
                    )
                )
            ),
        )

        with mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as json_response:
            result = await test_module.w3c_creds_list(self.request)
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
        self.profile.context.injector.bind_instance(
            VCHolder,
            mock.MagicMock(
                search_credentials=mock.MagicMock(
                    return_value=mock.MagicMock(
                        fetch=mock.CoroutineMock(
                            side_effect=test_module.StorageNotFoundError()
                        )
                    )
                )
            ),
        )

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
        self.profile.context.injector.bind_instance(
            VCHolder,
            mock.MagicMock(
                search_credentials=mock.MagicMock(
                    return_value=mock.MagicMock(
                        fetch=mock.CoroutineMock(side_effect=test_module.StorageError())
                    )
                )
            ),
        )

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
