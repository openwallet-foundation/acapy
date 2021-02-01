"""Test did resolver registery."""

import pytest
import unittest
from ..did_resolver_registry import DIDResolverRegistry


def test_create_registry():
    did_resolver_registry = DIDResolverRegistry()
    test_resolver = unittest.mock.MagicMock()
    did_resolver_registry.register(test_resolver)
    assert did_resolver_registry.did_resolvers == [test_resolver]
