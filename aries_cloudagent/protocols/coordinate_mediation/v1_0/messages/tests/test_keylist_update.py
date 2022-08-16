"""Test keylist update message."""
from unittest import TestCase

from ...message_types import KEYLIST_UPDATE
from ..inner.keylist_update_rule import KeylistUpdateRule
from ..keylist_update import KeylistUpdate, KeylistUpdateSchema
from . import MessageTest


class TestKeylistUpdate(MessageTest, TestCase):
    """Test keylist update message."""

    TYPE = KEYLIST_UPDATE
    CLASS = KeylistUpdate
    SCHEMA = KeylistUpdateSchema
    VALUES = {
        "updates": [
            KeylistUpdateRule(
                "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL", "add"
            )
        ]
    }
