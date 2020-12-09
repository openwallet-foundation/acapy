"""Test keylist query message."""
from unittest import TestCase

from ...message_types import KEYLIST_QUERY
from ..inner.keylist_query_paginate import KeylistQueryPaginate
from ..keylist_query import KeylistQuery, KeylistQuerySchema
from . import MessageTest


class TestKeylistQuery(MessageTest, TestCase):
    """Test KeylistQuery message."""

    TYPE = KEYLIST_QUERY
    CLASS = KeylistQuery
    SCHEMA = KeylistQuerySchema
    VALUES = {
        "filter": {"filter": "something"},
        "paginate": KeylistQueryPaginate(10, 10),
    }
