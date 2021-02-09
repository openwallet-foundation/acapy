import unittest

import pytest
from asynctest import mock as async_mock

from ..base import (
    BaseDIDResolver,
    DIDMethodNotSupported,
    DIDNotFound,
    ResolverType,
)
from ...resolver.did import DID
from ...resolver.diddoc import ResolvedDIDDoc
from ..did_resolver import DIDResolver
from ..did_resolver_registry import DIDResolverRegistry
from .test_did_resolver import TEST_DID_METHODS
from ...admin.request_context import AdminRequestContext
from .test_diddoc import DOC
from .. import routes as test_module


context = AdminRequestContext.test_context({})
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
did_doc = ResolvedDIDDoc(DOC)

def test_resolver():
    with async_mock.patch.object(
        test_module.resolve_did.resolver, "resolve", async_mock.CoroutineMock(
            return_value=did_doc
            )
    ) as resolver_api:
        result = resolver_api.resolve_did(request)
        assert result == did_doc
