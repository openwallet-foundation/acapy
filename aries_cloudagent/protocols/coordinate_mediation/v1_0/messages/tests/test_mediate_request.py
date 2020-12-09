"""Test mediate request message."""
from unittest import TestCase

from ...message_types import MEDIATE_REQUEST
from ..mediate_request import MediationRequest, MediationRequestSchema
from . import MessageTest


class TestMediateRequest(MessageTest, TestCase):
    """Test mediate request message."""

    TYPE = MEDIATE_REQUEST
    CLASS = MediationRequest
    SCHEMA = MediationRequestSchema
    VALUES = {"mediator_terms": ["test", "terms"], "recipient_terms": ["test", "terms"]}
