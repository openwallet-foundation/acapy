"""Test resolver routes."""

# pylint: disable=redefined-outer-name

import pytest
from asynctest import mock as async_mock
from pydid import DIDDocument

from ...admin.request_context import AdminRequestContext
from .. import routes as test_module
from ..base import (
    DIDMethodNotSupported,
    DIDNotFound,
    ResolutionMetadata,
    ResolutionResult,
    ResolverError,
    ResolverType,
)
from ..did_resolver import DIDResolver
from . import DOC


@pytest.fixture
def did_doc():
    yield DIDDocument.deserialize(DOC)


@pytest.fixture
def resolution_result(did_doc):
    metadata = ResolutionMetadata(
        resolver_type=ResolverType.NATIVE,
        resolver="mock_resolver",
        retrieved_time="some time",
        duration=10,
    )
    yield ResolutionResult(did_doc, metadata)


@pytest.fixture
def mock_response():
    json_response = async_mock.MagicMock()
    temp_value = test_module.web.json_response
    test_module.web.json_response = json_response
    yield json_response
    test_module.web.json_response = temp_value


@pytest.fixture
def mock_resolver(resolution_result):
    did_resolver = async_mock.MagicMock()
    did_resolver.resolve = async_mock.CoroutineMock(return_value=did_doc)
    did_resolver.resolve_with_metadata = async_mock.CoroutineMock(
        return_value=resolution_result
    )
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
async def test_resolver(mock_request, mock_response: async_mock.MagicMock, did_doc):
    await test_module.resolve_did(mock_request)
    mock_response.call_args[0][0] == did_doc.serialize()
    # TODO: test http response codes


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "side_effect, error",
    [
        (DIDNotFound, test_module.web.HTTPNotFound),
        (DIDMethodNotSupported, test_module.web.HTTPNotImplemented),
        (ResolverError, test_module.web.HTTPInternalServerError),
    ],
)
async def test_resolver_not_found_error(
    mock_resolver, mock_request, side_effect, error
):
    mock_resolver.resolve_with_metadata = async_mock.CoroutineMock(
        side_effect=side_effect()
    )
    with pytest.raises(error):
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
