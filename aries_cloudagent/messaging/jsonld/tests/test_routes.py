import pytest
import unittest
import asyncio
import pytest
from asynctest import mock as async_mock
from ....messaging.models.base import BaseModelError
from ....wallet.error import WalletError
from ....config.base import InjectionError
from ....storage.error import StorageError, StorageNotFoundError
from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from ....admin.request_context import AdminRequestContext
from .. import credential
from .. import routes as test_module
from ....resolver.did_resolver import DIDResolver
from ....resolver.base import DIDNotFound, DIDMethodNotSupported
from ....resolver.tests import DOC
from ....connections.models.diddoc_v2.diddoc import DIDDoc

did_doc = DIDDoc.deserialize(DOC)


@pytest.fixture
def mock_resolver():
    did_resolver = async_mock.MagicMock()
    did_resolver.resolve = async_mock.CoroutineMock(return_value=did_doc)
    url = "did:example:1234abcd#4"
    did_resolver.dereference = async_mock.CoroutineMock(
        return_value=did_doc.dereference(url)
    )
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
def mock_sign_request(mock_sign_credential, mock_resolver):
    context = AdminRequestContext.test_context({DIDResolver: mock_resolver})
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
def mock_verify_request(mock_verify_credential, mock_resolver):
    context = AdminRequestContext.test_context({DIDResolver: mock_resolver})
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
                        "verificationMethod": "did:key:z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd#z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd",
                    },
                }
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
async def test_sign(mock_sign_request, mock_response):
    await test_module.sign(mock_sign_request)
    mock_response.assert_called_once_with({"signed_doc": "fake_signage"})


@pytest.mark.parametrize(
    "error", [DIDNotFound, DIDMethodNotSupported, WalletError, InjectionError]
)
@pytest.mark.asyncio
async def test_sign_bad_req_error(mock_sign_request, mock_response, error):
    test_module.sign_credential = async_mock.CoroutineMock(side_effect=error())
    with pytest.raises(test_module.web.HTTPBadRequest):
        await test_module.sign(mock_sign_request)


@pytest.mark.asyncio
async def test_sign_bad_ver_meth_deref_req_error(
    mock_resolver, mock_sign_request, mock_response
):
    mock_resolver.dereference.return_value = None
    with pytest.raises(test_module.web.HTTPBadRequest):
        await test_module.sign(mock_sign_request)


@pytest.mark.asyncio
async def test_verify(mock_verify_request, mock_response):
    await test_module.verify(mock_verify_request)
    mock_response.assert_called_once_with({"valid": "fake_verify"})


@pytest.mark.parametrize(
    "error", [DIDNotFound, DIDMethodNotSupported, WalletError, InjectionError]
)
@pytest.mark.asyncio
async def test_verify_bad_req_error(mock_verify_request, mock_response, error):
    test_module.verify_credential = async_mock.CoroutineMock(side_effect=error())
    with pytest.raises(test_module.web.HTTPBadRequest):
        await test_module.verify(mock_verify_request)


@pytest.mark.asyncio
async def test_verify_bad_ver_meth_deref_req_error(
    mock_resolver, mock_verify_request, mock_response
):
    mock_resolver.dereference.return_value = None
    with pytest.raises(test_module.web.HTTPBadRequest):
        await test_module.verify(mock_verify_request)


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
