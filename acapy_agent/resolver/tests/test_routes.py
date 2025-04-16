"""Test resolver routes."""

# pylint: disable=redefined-outer-name

import pytest
import pytest_asyncio
from pydid import DIDDocument

from ...admin.request_context import AdminRequestContext
from ...tests import mock
from ...utils.testing import create_test_profile
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
    json_response = mock.MagicMock()
    temp_value = test_module.web.json_response
    test_module.web.json_response = json_response
    yield json_response
    test_module.web.json_response = temp_value


@pytest.fixture
def mock_resolver(resolution_result):
    did_resolver = mock.MagicMock(DIDResolver, autospec=True)
    did_resolver.resolve = mock.CoroutineMock(return_value=did_doc)
    did_resolver.resolve_with_metadata = mock.CoroutineMock(
        return_value=resolution_result
    )
    yield did_resolver


@pytest_asyncio.fixture
async def profile():
    profile = await create_test_profile(
        settings={
            "admin.admin_api_key": "secret-key",
        }
    )
    yield profile


@pytest.mark.asyncio
async def test_resolver(profile, mock_resolver, mock_response: mock.MagicMock, did_doc):
    profile.context.injector.bind_instance(DIDResolver, mock_resolver)
    context = AdminRequestContext.test_context({}, profile)

    outbound_message_router = mock.CoroutineMock()
    request_dict = {
        "context": context,
        "outbound_message_router": outbound_message_router,
    }
    request = mock.MagicMock(
        match_info={
            "did": "did:ethr:mainnet:0xb9c5714089478a327f09197987f16f9e5d936e8a",
        },
        query={},
        json=mock.CoroutineMock(return_value={}),
        __getitem__=lambda _, k: request_dict[k],
        headers={"x-api-key": "secret-key"},
    )
    await test_module.resolve_did(request)
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
async def test_resolver_not_found_error(profile, mock_resolver, side_effect, error):
    mock_resolver.resolve_with_metadata = mock.CoroutineMock(side_effect=side_effect())
    context = AdminRequestContext.test_context({}, profile)
    profile.context.injector.bind_instance(DIDResolver, mock_resolver)

    outbound_message_router = mock.CoroutineMock()
    request_dict = {
        "context": context,
        "outbound_message_router": outbound_message_router,
    }
    request = mock.MagicMock(
        match_info={
            "did": "did:ethr:mainnet:0xb9c5714089478a327f09197987f16f9e5d936e8a",
        },
        query={},
        json=mock.CoroutineMock(return_value={}),
        __getitem__=lambda _, k: request_dict[k],
        headers={"x-api-key": "secret-key"},
    )
    with pytest.raises(error):
        await test_module.resolve_did(request)


@pytest.mark.asyncio
async def test_register():
    mock_app = mock.MagicMock()
    mock_app.add_routes = mock.MagicMock()
    await test_module.register(mock_app)
    mock_app.add_routes.assert_called_once()


@pytest.mark.asyncio
async def test_post_process_routes():
    mock_app = mock.MagicMock(_state={"swagger_dict": {}})
    test_module.post_process_routes(mock_app)
    assert "tags" in mock_app._state["swagger_dict"]
