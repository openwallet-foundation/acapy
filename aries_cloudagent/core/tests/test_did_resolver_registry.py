"""Test DID class."""

import pytest
import unittest
from ..did_resolver_registry import DIDResolverRegistry


def test_create_registry():
    resolver = DIDResolverRegistry()
    test_resolver = unittest.mock.MagicMock()
    resolver.register(test_resolver)
    assert resolver.did_resolvers == [test_resolver]
