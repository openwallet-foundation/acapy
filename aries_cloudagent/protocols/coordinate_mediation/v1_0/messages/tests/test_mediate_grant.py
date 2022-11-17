"""Test mediate grant message."""
from unittest import TestCase

from ...message_types import MEDIATE_GRANT
from ..mediate_grant import MediationGrant, MediationGrantSchema
from . import MessageTest


class TestMediateGrant(MessageTest, TestCase):
    """Test mediate grant message."""

    TYPE = MEDIATE_GRANT
    CLASS = MediationGrant
    SCHEMA = MediationGrantSchema
    VALUES = {
        "endpoint": "http://localhost:3000",
        "routing_keys": ["did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"],
    }
