"""Test keylist update response message."""
from unittest import TestCase

from ...message_types import KEYLIST_UPDATE_RESPONSE
from ..inner.keylist_updated import KeylistUpdated
from ..keylist_update_response import KeylistUpdateResponse, KeylistUpdateResponseSchema
from . import MessageTest


class TestKeylistUpdateResponse(MessageTest, TestCase):
    """Test keylist update response message."""

    TYPE = KEYLIST_UPDATE_RESPONSE
    CLASS = KeylistUpdateResponse
    SCHEMA = KeylistUpdateResponseSchema
    VALUES = {
        "updated": [
            KeylistUpdated(
                recipient_key="3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx",
                action="added",
                result="success",
            )
        ]
    }
