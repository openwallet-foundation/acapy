from copy import deepcopy
import json

from aiohttp import web
from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock
from pyld import jsonld
import pytest

from .. import routes as test_module
from ....admin.request_context import AdminRequestContext
from ....config.base import InjectionError
from ....resolver.base import DIDMethodNotSupported, DIDNotFound, ResolverError
from ....resolver.did_resolver import DIDResolver
from ....vc.ld_proofs.document_loader import DocumentLoader
from ....wallet.base import BaseWallet
from ....wallet.did_method import SOV, DIDMethods
from ....wallet.error import WalletError
from ....wallet.key_type import ED25519
from ..error import (
    BadJWSHeaderError,
    DroppedAttributeError,
    MissingVerificationMethodError,
)
from .document_loader import custom_document_loader


@pytest.fixture
def did_doc():
    yield {
        "@context": "https://w3id.org/did/v1",
        "id": "did:example:1234abcd",
        "verificationMethod": [
            {
                "id": "did:example:1234abcd#key-1",
                "type": "Ed25519VerificationKey2018",
                "controller": "did:example:1234abcd",
                "publicKeyBase58": "12345",
            },
            {
                "id": "did:example:1234abcd#key-2",
                "type": "RsaVerificationKey2018",
                "controller": "did:example:1234abcd",
                "publicKeyJwk": {},
            },
        ],
        "service": [
            {
                "id": "did:example:1234abcd#did-communication",
                "type": "did-communication",
                "priority": 0,
                "recipientKeys": ["did:example:1234abcd#4"],
                "routingKeys": ["did:example:1234abcd#6"],
                "serviceEndpoint": "http://example.com",
            }
        ],
    }


@pytest.fixture
def mock_resolver(did_doc):
    did_resolver = DIDResolver(async_mock.MagicMock())
    did_resolver.resolve = async_mock.CoroutineMock(return_value=did_doc)
    yield did_resolver


@pytest.fixture
def mock_sign_credential():
    temp = test_module.sign_credential
    sign_credential = async_mock.CoroutineMock(return_value="fake_signage")
    test_module.sign_credential = sign_credential
    yield test_module.sign_credential
    test_module.sign_credential = temp


@pytest.fixture
def mock_verify_credential():
    temp = test_module.verify_credential
    verify_credential = async_mock.CoroutineMock(return_value="fake_verify")
    test_module.verify_credential = verify_credential
    yield test_module.verify_credential
    test_module.verify_credential = temp


@pytest.fixture
def mock_sign_request(mock_sign_credential):
    context = AdminRequestContext.test_context()
    outbound_message_router = async_mock.CoroutineMock()
    request_dict = {
        "context": context,
        "outbound_message_router": outbound_message_router,
    }
    request = async_mock.MagicMock(
        match_info={},
        query={},
        json=async_mock.CoroutineMock(
            return_value={
                "verkey": "fake_verkey",
                "doc": {},
                "options": {
                    "type": "Ed25519Signature2018",
                    "created": "2020-04-10T21:35:35Z",
                    "verificationMethod": (
                        "did:key:"
                        "z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd#"
                        "z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd"
                    ),
                    "proofPurpose": "assertionMethod",
                },
            },
        ),
        __getitem__=lambda _, k: request_dict[k],
    )
    yield request


@pytest.fixture
def request_body():
    yield {
        "doc": {
            "@context": "https://www.w3.org/2018/credentials/v1",
            "type": "VerifiablePresentation",
            "holder": "did:key:z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd",
            "proof": {
                "type": "Ed25519Signature2018",
                "created": "2021-02-16T15:21:38.512Z",
                "challenge": "5103d61a-bd26-4b1a-ab62-87a2a71281d3",
                "domain": "svip-issuer.ocs-support.com",
                "jws": "eyJhbGciOiJFZERTQSIsImI2NCI6ZmFsc2UsImNyaXQiOlsiYjY0Il19..mH_j_Y7MUIu_KXU_1Dy1BjE4w52INieSPaN7FPtKQKZYTRydPYO5jbjeM-uWB5BXpxS9o-obI5Ztx5IXex-9Aw",
                "proofPurpose": "authentication",
                "verificationMethod": "did:example:1234abcd#key-1",
            },
        }
    }


@pytest.fixture
def mock_verify_request(mock_verify_credential, mock_resolver, request_body):
    def _mock_verify_request(request_body=request_body):
        context = AdminRequestContext.test_context({DIDResolver: mock_resolver})
        outbound_message_router = async_mock.CoroutineMock()
        request_dict = {
            "context": context,
            "outbound_message_router": outbound_message_router,
        }
        request = async_mock.MagicMock(
            match_info={},
            query={},
            json=async_mock.CoroutineMock(return_value=request_body),
            __getitem__=lambda _, k: request_dict[k],
        )
        return request

    yield _mock_verify_request


@pytest.fixture
def mock_response():
    json_response = async_mock.MagicMock()
    temp_value = test_module.web.json_response
    test_module.web.json_response = json_response
    yield json_response
    test_module.web.json_response = temp_value


@pytest.mark.asyncio
async def test_sign(mock_sign_request, mock_response):
    await test_module.sign(mock_sign_request)
    mock_response.assert_called_once_with({"signed_doc": "fake_signage"})
    assert "error" not in mock_response.call_args[0][0]


@pytest.mark.parametrize(
    "error", [DroppedAttributeError, MissingVerificationMethodError]
)
@pytest.mark.asyncio
async def test_sign_bad_req_error(mock_sign_request, mock_response, error):
    test_module.sign_credential = async_mock.CoroutineMock(side_effect=error())
    await test_module.sign(mock_sign_request)
    assert "error" in mock_response.call_args[0][0]


@pytest.mark.parametrize("error", [WalletError])
@pytest.mark.asyncio
async def test_sign_bad_req_http_error(mock_sign_request, mock_response, error):
    test_module.sign_credential = async_mock.CoroutineMock(side_effect=error())
    with pytest.raises(web.HTTPForbidden):
        await test_module.sign(mock_sign_request)


@pytest.mark.asyncio
async def test_verify(mock_verify_request, mock_response):
    await test_module.verify(mock_verify_request())
    mock_response.assert_called_once_with({"valid": "fake_verify"})


@pytest.mark.parametrize(
    "error",
    [
        BadJWSHeaderError,
        DroppedAttributeError,
        ResolverError,
        DIDNotFound,
        DIDMethodNotSupported,
    ],
)
@pytest.mark.asyncio
async def test_verify_bad_req_error(mock_verify_request, mock_response, error):
    test_module.verify_credential = async_mock.CoroutineMock(side_effect=error())
    await test_module.verify(mock_verify_request())
    assert "error" in mock_response.call_args[0][0]


@pytest.mark.parametrize(
    "error",
    [
        WalletError,
        InjectionError,
    ],
)
@pytest.mark.asyncio
async def test_verify_bad_req_http_error(mock_verify_request, mock_response, error):
    test_module.verify_credential = async_mock.CoroutineMock(side_effect=error())
    with pytest.raises(web.HTTPForbidden):
        await test_module.verify(mock_verify_request())


@pytest.mark.asyncio
async def test_verify_bad_ver_meth_deref_req_error(
    mock_resolver, mock_verify_request, mock_response
):
    mock_resolver.dereference = async_mock.CoroutineMock(side_effect=ResolverError)
    await test_module.verify(mock_verify_request())
    assert "error" in mock_response.call_args[0][0]


@pytest.mark.parametrize(
    "vmethod",
    [
        "did:example:1234abcd#key-2",
        "did:example:1234abcd#did-communication",
    ],
)
@pytest.mark.asyncio
async def test_verify_bad_vmethod_unsupported(
    mock_resolver,
    mock_verify_request,
    mock_response,
    request_body,
    vmethod,
):
    request_body["doc"]["proof"]["verificationMethod"] = vmethod
    with pytest.raises(web.HTTPBadRequest):
        await test_module.verify(mock_verify_request(request_body))


@pytest.mark.asyncio
async def test_register():
    mock_app = async_mock.MagicMock()
    mock_app.add_routes = async_mock.MagicMock()
    await test_module.register(mock_app)
    mock_app.add_routes.assert_called_once()


def test_post_process_routes():
    mock_app = async_mock.MagicMock(_state={"swagger_dict": {}})
    test_module.post_process_routes(mock_app)
    assert "tags" in mock_app._state["swagger_dict"]


class TestJSONLDRoutes(AsyncTestCase):
    async def setUp(self):
        self.context = AdminRequestContext.test_context()
        self.context.profile.context.injector.bind_instance(
            DocumentLoader, custom_document_loader
        )
        self.context.profile.context.injector.bind_instance(DIDMethods, DIDMethods())
        self.did_info = await (await self.context.session()).wallet.create_local_did(
            SOV, ED25519
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
                            "name": "Bachelor of Encyclopædic Arts",
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
        mock_app.add_routes.assert_called_once()
