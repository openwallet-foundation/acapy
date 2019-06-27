from asynctest import TestCase as AsyncTestCase

from ...messaging.protocol_registry import ProtocolRegistry
from ...messaging.serializer import MessageSerializer
from ...transport.outbound.queue.base import BaseOutboundMessageQueue

from ..default_context import DefaultContextBuilder
from ..injection_context import InjectionContext


class TestDefaultContext(AsyncTestCase):
    async def test_build_context(self):
        """Test context init."""

        builder = DefaultContextBuilder()
        result = await builder.build()
        assert isinstance(result, InjectionContext)

        for cls in (BaseOutboundMessageQueue, MessageSerializer, ProtocolRegistry):
            assert isinstance(await result.inject(cls), cls)
