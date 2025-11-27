import re
from unittest import IsolatedAsyncioTestCase

from ....core.event_bus import MockEventBus
from ...events import (
    CRED_DEF_FINISHED_EVENT,
    REV_LIST_CREATE_REQUESTED_EVENT,
    REV_LIST_CREATE_RESPONSE_EVENT,
    REV_LIST_FINISHED_EVENT,
    REV_LIST_STORE_REQUESTED_EVENT,
    REV_LIST_STORE_RESPONSE_EVENT,
    REV_REG_ACTIVATION_REQUESTED_EVENT,
    REV_REG_ACTIVATION_RESPONSE_EVENT,
    REV_REG_DEF_CREATE_REQUESTED_EVENT,
    REV_REG_DEF_CREATE_RESPONSE_EVENT,
    REV_REG_DEF_STORE_REQUESTED_EVENT,
    REV_REG_DEF_STORE_RESPONSE_EVENT,
    REV_REG_FULL_DETECTED_EVENT,
    REV_REG_FULL_HANDLING_COMPLETED_EVENT,
)
from ...revocation import routes as test_module


class TestRevocationRoutes(IsolatedAsyncioTestCase):
    def test_register_events(self):
        """Test handlers are added on register.

        This test need not be particularly in depth to keep it from getting brittle.
        """
        event_bus = MockEventBus()
        test_module.register_events(event_bus)
        for pattern in [
            CRED_DEF_FINISHED_EVENT,
            REV_REG_DEF_CREATE_REQUESTED_EVENT,
            REV_REG_DEF_CREATE_RESPONSE_EVENT,
            REV_REG_DEF_STORE_REQUESTED_EVENT,
            REV_REG_DEF_STORE_RESPONSE_EVENT,
            REV_LIST_CREATE_REQUESTED_EVENT,
            REV_LIST_CREATE_RESPONSE_EVENT,
            REV_LIST_STORE_REQUESTED_EVENT,
            REV_LIST_STORE_RESPONSE_EVENT,
            REV_LIST_FINISHED_EVENT,
            REV_REG_ACTIVATION_REQUESTED_EVENT,
            REV_REG_ACTIVATION_RESPONSE_EVENT,
            REV_REG_FULL_DETECTED_EVENT,
            REV_REG_FULL_HANDLING_COMPLETED_EVENT,
        ]:
            assert re.compile(pattern) in event_bus.topic_patterns_to_subscribers
