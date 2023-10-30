"""Test keylist message."""
from unittest import TestCase

from ...message_types import KEYLIST
from ..inner.keylist_key import KeylistKey
from ..inner.keylist_query_paginate import KeylistQueryPaginate
from ..keylist import Keylist, KeylistSchema
from . import MessageTest


class TestKeylist(MessageTest, TestCase):
    """Test Keylist message."""

    TYPE = KEYLIST
    CLASS = Keylist
    SCHEMA = KeylistSchema
    VALUES = {
        "pagination": KeylistQueryPaginate(10, 10),
        "keys": [
            KeylistKey(
                recipient_key="did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                action="added",
                result="success",
            )
        ],
    }
