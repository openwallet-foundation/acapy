from unittest import IsolatedAsyncioTestCase

from ....core.event_bus import MockEventBus
from ...events import (
    CRED_DEF_FINISHED_PATTERN,
    REV_LIST_FINISHED_PATTERN,
    REV_REG_DEF_FINISHED_PATTERN,
)
from ...revocation import routes as test_module


class TestRevocationRoutes(IsolatedAsyncioTestCase):
    def test_register_events(self):
        """Test handlers are added on register.

        This test need not be particularly in depth to keep it from getting brittle.
        """
        event_bus = MockEventBus()
        test_module.register_events(event_bus)
        assert all(
            pattern in event_bus.topic_patterns_to_subscribers
            for pattern in [
                CRED_DEF_FINISHED_PATTERN,
                REV_REG_DEF_FINISHED_PATTERN,
                REV_LIST_FINISHED_PATTERN,
            ]
        )
