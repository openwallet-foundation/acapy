import unittest
import asyncio
import pytest
from asynctest import mock as async_mock
from ...storage.error import StorageError, StorageNotFoundError
from ...messaging.models.base import BaseModelError

from ..base import (
    BaseDIDResolver,
    DIDMethodNotSupported,
    DIDNotFound,
    ResolverType,
)
from ...resolver.did import DID
from . import DOC
from ...connections.models.diddoc_v2.diddoc import DIDDoc
from ..did_resolver import DIDResolver
from ..did_resolver_registry import DIDResolverRegistry
from .test_did_resolver import TEST_DID_METHODS
from ...admin.request_context import AdminRequestContext
from .. import routes as test_module
from ...core.in_memory import InMemoryProfile

did_doc = DIDDoc.deserialize(DOC)


@pytest.fixture
def mock_response():
    json_response = async_mock.MagicMock()
    temp_value = test_module.web.json_response
    test_module.web.json_response = json_response
    yield json_response
    test_module.web.json_response = temp_value


@pytest.fixture
def mock_resolver():
    did_resolver = async_mock.MagicMock()
    did_resolver.resolve = async_mock.CoroutineMock(return_value=did_doc)
    yield did_resolver


@pytest.fixture
def mock_request(mock_resolver):
    context = AdminRequestContext.test_context({DIDResolver: mock_resolver})
    outbound_message_router = async_mock.CoroutineMock()
    request_dict = {
        "context": context,
        "outbound_message_router": outbound_message_router,
    }
    request = async_mock.MagicMock(
        match_info={
            "did": "did:ethr:mainnet:0xb9c5714089478a327f09197987f16f9e5d936e8a",
        },
        query={},
        json=async_mock.CoroutineMock(return_value={}),
        __getitem__=lambda _, k: request_dict[k],
    )
    yield request


@pytest.mark.asyncio
async def test_resolver(mock_request, mock_response):
    await test_module.resolve_did(mock_request)
    mock_response.assert_called_once_with(did_doc.serialize())
    # TODO: test http response codes


@pytest.mark.asyncio
async def test_resolver_not_found_error(mock_resolver, mock_request, mock_response):
    mock_resolver.resolve = async_mock.CoroutineMock(side_effect=StorageNotFoundError())
    with pytest.raises(test_module.web.HTTPNotFound):
        await test_module.resolve_did(mock_request)


@pytest.mark.asyncio
async def test_resolver_bad_req_error(mock_resolver, mock_request, mock_response):
    mock_resolver.resolve = async_mock.CoroutineMock(side_effect=BaseModelError())
    with pytest.raises(test_module.web.HTTPBadRequest):
        await test_module.resolve_did(mock_request)


@pytest.mark.asyncio
async def test_resolver_bad_req_storage_error(
    mock_resolver, mock_request, mock_response
):
    mock_resolver.resolve = async_mock.CoroutineMock(side_effect=StorageError())
    with pytest.raises(test_module.web.HTTPBadRequest):
        await test_module.resolve_did(mock_request)


@pytest.mark.asyncio
async def test_register():
    mock_app = async_mock.MagicMock()
    mock_app.add_routes = async_mock.MagicMock()
    await test_module.register(mock_app)
    mock_app.add_routes.assert_called_once()


@pytest.mark.asyncio
async def test_post_process_routes():
    mock_app = async_mock.MagicMock(_state={"swagger_dict": {}})
    test_module.post_process_routes(mock_app)
    assert "tags" in mock_app._state["swagger_dict"]
