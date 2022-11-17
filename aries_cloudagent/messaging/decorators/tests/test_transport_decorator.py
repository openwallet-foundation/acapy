from unittest import TestCase

from ...valid import UUIDFour
from ..transport_decorator import TransportDecorator, TransportDecoratorSchema


class TestTransportDecorator(TestCase):
    def test_serialize_load(self):
        deco = TransportDecorator(
            return_route="all",
            return_route_thread=UUIDFour.EXAMPLE,
            queued_message_count=23,
        )

        assert deco.return_route == "all"
        assert deco.return_route_thread == UUIDFour.EXAMPLE
        assert deco.queued_message_count == 23

        dumped = deco.serialize()
        loaded = TransportDecorator.deserialize(dumped)
