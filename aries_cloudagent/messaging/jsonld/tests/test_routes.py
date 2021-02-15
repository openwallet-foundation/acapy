import pytest
import unittest
import asyncio
import pytest
from asynctest import mock as async_mock
from ....messaging.models.base import BaseModelError
from ....storage.error import StorageError, StorageNotFoundError
from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from ....admin.request_context import AdminRequestContext
from .. import credential
from .. import routes as test_module


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
def mock_request(mock_sign_credential, mock_verify_credential):
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
                            "did:key:"
                            "z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd"
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
            }
        ),
        __getitem__=lambda _, k: request_dict[k],
    )
    yield request


@pytest.fixture
def mock_response():
    json_response = async_mock.MagicMock()
    temp_value = test_module.web.json_response
    test_module.web.json_response = json_response
    yield json_response
    test_module.web.json_response = temp_value


@pytest.mark.asyncio
async def test_sign(mock_sign_credential, mock_request, mock_response):
    await test_module.sign(mock_request)
    mock_response.assert_called_once_with({"signed_doc": "fake_signage"})


@pytest.mark.asyncio
async def test_sign_key_not_found_error(
    mock_sign_credential, mock_request, mock_response
):
    test_module.sign_credential = async_mock.CoroutineMock(side_effect=StorageNotFoundError())
    with pytest.raises(test_module.web.HTTPNotFound):
        await test_module.sign(mock_request)


@pytest.mark.parametrize("error", [BaseModelError, StorageError])
@pytest.mark.asyncio
async def test_sign_bad_req_error(
    mock_sign_credential, mock_request, mock_response, error
):
    test_module.sign_credential = async_mock.CoroutineMock(side_effect=error())
    with pytest.raises(test_module.web.HTTPBadRequest):
        await test_module.sign(mock_request)


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
        self.session_inject = {}
        self.context = AdminRequestContext.test_context(self.session_inject)
        self.did_info = await (await self.context.session()).wallet.create_local_did()
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

    """
        [
        {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://www.w3.org/2018/credentials/examples/v1"
        ],
        "id": "http://example.gov/credentials/3732",
        "type": [
            "VerifiableCredential",
            "UniversityDegreeCredential"
        ],
        "issuer": "did:key:z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd",
        "issuanceDate": "2020-03-16T22:37:26.544Z",
        "expirationDate": "2020-03-16T22:37:26.544Z",
        "credentialSubject": {
            "id": "did:example:123",
            "degree": {
            "type": "BachelorDegree",
            "name": "Bachelor of Science and Arts"
            }
        },
        "proof": {
            "type": "Ed25519Signature2018",
            "created": "2020-04-02T18:28:08Z",
            "verificationMethod": "did:example:123#z6MksHh7qHWvybLg5QTPPdG2DgEjjduBDArV9EF9mRiRzMBN",
            "proofPurpose": "assertionMethod",
            "jws": "eyJhbGciOiJFZERTQSIsImI2NCI6ZmFsc2UsImNyaXQiOlsiYjY0Il19..YtqjEYnFENT7fNW-COD0HAACxeuQxPKAmp4nIl8jYAu__6IH2FpSxv81w-l5PvE1og50tS9tH8WyXMlXyo45CA"
        }
        },
        ...]
    """

    async def test_verify_credential(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={  # posted json
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
                    "issuer": (
                        "did:key:z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd"
                    ),
                    "issuanceDate": "2020-03-10T04:24:12.164Z",
                    "credentialSubject": {
                        "id": (
                            "did:key:"
                            "z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd"
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
        )

        with async_mock.patch.object(test_module.web, "json_response") as mock_response:
            result = await test_module.verify(self.request)
            assert result == mock_response.return_value
            mock_response.assert_called_once_with({"valid": True})  # expected response

    async def test_sign_credential(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={  # posted json
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
                            "did:key:"
                            "z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd"
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
            }
        )

        with async_mock.patch.object(test_module.web, "json_response") as mock_response:
            result = await test_module.sign(self.request)
            assert result == mock_response.return_value
            mock_response.assert_called_once()
            assert "signed_doc" in mock_response.call_args[0][0]
            assert "error" not in mock_response.call_args[0][0]
