import json

from copy import deepcopy

from asynctest import mock as async_mock, TestCase as AsyncTestCase
from pyld import jsonld

from ....admin.request_context import AdminRequestContext
from ....wallet.crypto import KeyType, DIDMethod
from ....wallet.base import BaseWallet

from .. import routes as test_module


class TestJSONLDRoutes(AsyncTestCase):
    async def setUp(self):
        self.context = AdminRequestContext.test_context()
        self.did_info = await (await self.context.session()).wallet.create_local_did(
            DIDMethod.SOV, KeyType.ED25519
        )
        self.request_dict = {
            "context": self.context,
            "outbound_message_router": async_mock.CoroutineMock(),
        }
        self.request = async_mock.MagicMock(
            app={},
            match_info={},
            query={},
            __getitem__=lambda _, k: self.request_dict[k],
        )

    async def test_verify_credential(self):
        POSTED_REQUEST = {  # posted json
            "verkey": (
                # pulled from the did:key in example
                "5yKdnU7ToTjAoRNDzfuzVTfWBH38qyhE1b9xh4v8JaWF"
            ),
            "doc": {
                "@context": [
                    "https://www.w3.org/2018/credentials/v1",
                    "https://www.w3.org/2018/credentials/examples/v1",
                ],
                "id": "http://example.gov/credentials/3732",
                "type": ["VerifiableCredential", "UniversityDegreeCredential"],
                "issuer": ("did:key:z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd"),
                "issuanceDate": "2020-03-10T04:24:12.164Z",
                "credentialSubject": {
                    "id": (
                        "did:key:" "z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd"
                    ),
                    "degree": {
                        "type": "BachelorDegree",
                        "name": "Bachelor of Science and Arts",
                    },
                },
                "proof": {
                    "type": "Ed25519Signature2018",
                    "created": "2020-04-10T21:35:35Z",
                    "verificationMethod": (
                        "did:key:"
                        "z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc"
                        "4tXLt9DoHd#z6MkjRagNiMu91DduvCvgEsqLZD"
                        "VzrJzFrwahc4tXLt9DoHd"
                    ),
                    "proofPurpose": "assertionMethod",
                    "jws": (
                        "eyJhbGciOiJFZERTQSIsImI2NCI6ZmFsc2UsImNyaX"
                        "QiOlsiYjY0Il19..l9d0YHjcFAH2H4dB9xlWFZQLUp"
                        "ixVCWJk0eOt4CXQe1NXKWZwmhmn9OQp6YxX0a2Lffe"
                        "gtYESTCJEoGVXLqWAA"
                    ),
                },
            },
        }

        self.request.json = async_mock.CoroutineMock(return_value=POSTED_REQUEST)

        with async_mock.patch.object(test_module.web, "json_response") as mock_response:
            result = await test_module.verify(self.request)
            assert result == mock_response.return_value
            mock_response.assert_called_once_with({"valid": True})  # expected response

        # compact, expand take a LONG TIME: do them once above, mock for error cases
        with async_mock.patch.object(
            jsonld, "compact", async_mock.MagicMock()
        ) as mock_compact, async_mock.patch.object(
            jsonld, "expand", async_mock.MagicMock()
        ) as mock_expand, async_mock.patch.object(
            test_module.web, "json_response", async_mock.MagicMock()
        ) as mock_response:
            mock_expand.return_value = [async_mock.MagicMock()]
            mock_compact.return_value = {
                "@context": "...",
                "id": "...",
                "type": ["...", "..."],
                "proof": {},
                "https://www.w3.org/2018/credentials#credentialSubject": {
                    "id": "did:key:z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd",
                    "https://example.org/examples#degree": {
                        "type": "https://example.org/examples#BachelorDegree",
                        "http://schema.org/name": {
                            "type": "http://www.w3.org/1999/02/22-rdf-syntax-ns#HTML",
                            "@value": "Bachelor of Science and Arts",
                        },
                    },
                },
                "https://www.w3.org/2018/credentials#issuanceDate": {
                    "type": "xsd:dateTime",
                    "@value": "2020-03-10T04:24:12.164Z",
                },
                "https://www.w3.org/2018/credentials#issuer": {
                    "id": "did:key:z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd"
                },
            }
            mock_response.side_effect = lambda x: json.dumps(x)
            result = await test_module.verify(self.request)
            assert "error" in json.loads(result)

        print("\n>> START X-ATTR-CRED-SUBJECT")
        with async_mock.patch.object(
            jsonld, "compact", async_mock.MagicMock()
        ) as mock_compact, async_mock.patch.object(
            jsonld, "expand", async_mock.MagicMock()
        ) as mock_expand, async_mock.patch.object(
            test_module.web, "json_response", async_mock.MagicMock()
        ) as mock_response:
            mock_expand.return_value = [async_mock.MagicMock()]
            mock_compact.return_value = {
                "@context": "...",
                "id": "...",
                "type": ["...", "..."],
                "proof": {
                    "type": "Ed25519Signature2018",
                    "created": "2020-04-10T21:35:35Z",
                    "jws": (
                        "eyJhbGciOiJFZERTQSIsImI2NCI6ZmFsc2UsImNyaXQiOlsiYjY0Il19"
                        ".."
                        "l9d0YHjcFAH2H4dB9xlWFZQLUpixVCWJk0eOt4CXQe1NXKWZwmhmn9OQ"
                        "p6YxX0a2LffegtYESTCJEoGVXLqWAA"
                    ),
                    "proofPurpose": "assertionMethod",
                    "verificationMethod": (
                        "did:key:z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd#"
                        "z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd"
                    ),
                },
                "https://www.w3.org/2018/credentials#credentialSubject": {
                    "id": "did:key:z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd",
                },
                "https://www.w3.org/2018/credentials#issuanceDate": {
                    "type": "xsd:dateTime",
                    "@value": "2020-03-10T04:24:12.164Z",
                },
                "https://www.w3.org/2018/credentials#issuer": {
                    "id": "did:key:z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd"
                },
            }
            mock_response.side_effect = lambda x: json.dumps(x)
            result = await test_module.verify(self.request)
            assert "error" in json.loads(result)

        self.context.session_inject[BaseWallet] = None
        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.verify(self.request)

    async def test_sign_credential(self):
        POSTED_REQUEST = {  # posted json
            "verkey": self.did_info.verkey,
            "doc": {
                "credential": {
                    "@context": [
                        "https://www.w3.org/2018/credentials/v1",
                        "https://www.w3.org/2018/credentials/examples/v1",
                    ],
                    "id": "http://example.gov/credentials/3732",
                    "type": [
                        "VerifiableCredential",
                        "UniversityDegreeCredential",
                    ],
                    "issuer": (
                        "did:key:" "z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd"
                    ),
                    "issuanceDate": "2020-03-10T04:24:12.164Z",
                    "credentialSubject": {
                        "id": (
                            "did:key:"
                            "z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd"
                        ),
                        "degree": {
                            "type": "BachelorDegree",
                            "name": u"Bachelor of Encyclopædic Arts",
                        },
                    },
                },
                "options": {
                    # "type": "Ed25519Signature2018",  exercise default
                    # "created": exercise default of now
                    "creator": (
                        "did:key:"
                        "z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd#"
                        "z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd"
                    ),
                    "verificationMethod": (
                        "did:key:"
                        "z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd#"
                        "z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd"
                    ),
                    "proofPurpose": "assertionMethod",
                },
            },
        }
        self.request.json = async_mock.CoroutineMock(return_value=POSTED_REQUEST)

        with async_mock.patch.object(test_module.web, "json_response") as mock_response:
            result = await test_module.sign(self.request)
            assert result == mock_response.return_value
            mock_response.assert_called_once()
            assert "signed_doc" in mock_response.call_args[0][0]
            assert "error" not in mock_response.call_args[0][0]

        # short circuit: does not reach expand/compact
        posted_request_x = deepcopy(POSTED_REQUEST)
        posted_request_x["doc"]["options"].pop("verificationMethod")
        posted_request_x["doc"]["options"].pop("creator")
        self.request.json = async_mock.CoroutineMock(return_value=posted_request_x)
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.MagicMock()
        ) as mock_response:
            mock_response.side_effect = lambda x: json.dumps(x)
            result = await test_module.sign(self.request)
            assert "error" in json.loads(result)

        # compact, expand take a LONG TIME: do them once above, mock for error cases
        posted_request = deepcopy(POSTED_REQUEST)
        self.request.json = async_mock.CoroutineMock(return_value=posted_request)
        with async_mock.patch.object(
            jsonld, "compact", async_mock.MagicMock()
        ) as mock_compact, async_mock.patch.object(
            jsonld, "expand", async_mock.MagicMock()
        ) as mock_expand, async_mock.patch.object(
            test_module.web, "json_response", async_mock.MagicMock()
        ) as mock_response:
            mock_expand.return_value = [async_mock.MagicMock()]
            mock_compact.return_value = {}  # drop all attributes
            mock_response.side_effect = lambda x: json.dumps(x)
            result = await test_module.sign(self.request)
            assert "error" in json.loads(result)

        self.context.session_inject[BaseWallet] = None
        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.sign(self.request)

    async def test_register(self):
        mock_app = async_mock.MagicMock()
        mock_app.add_routes = async_mock.MagicMock()

        await test_module.register(mock_app)
        assert mock_app.add_routes.call_count == 2
