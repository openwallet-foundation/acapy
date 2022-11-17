"""Test mediate deny message."""
from unittest import TestCase

from ...message_types import MEDIATE_DENY
from ..mediate_deny import MediationDeny, MediationDenySchema
from . import MessageTest


class TestMediateDeny(MessageTest, TestCase):
    """Test mediate deny message."""

    TYPE = MEDIATE_DENY
    CLASS = MediationDeny
    SCHEMA = MediationDenySchema
    VALUES = {"mediator_terms": ["test", "terms"], "recipient_terms": ["test", "terms"]}
