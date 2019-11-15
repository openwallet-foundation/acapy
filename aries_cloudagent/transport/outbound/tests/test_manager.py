import asyncio

from asynctest import TestCase as AsyncTestCase, mock as async_mock

from ....config.injection_context import InjectionContext
from ....connections.models.connection_target import ConnectionTarget

from ..manager import OutboundTransportManager, OutboundTransportRegistrationError
from ..message import OutboundMessage


class TestOutboundTransportManager(AsyncTestCase):
    def test_register_path(self):
        mgr = OutboundTransportManager(InjectionContext())
        mgr.register("http")
        assert mgr.get_registered_transport_for_scheme("http")

        with self.assertRaises(OutboundTransportRegistrationError):
            mgr.register("http")

    async def test_send_message(self):
        context = InjectionContext()
        mgr = OutboundTransportManager(context)

        transport_cls = async_mock.Mock(spec=[])
        with self.assertRaises(OutboundTransportRegistrationError):
            mgr.register_class(transport_cls, "transport_cls")

        transport = async_mock.MagicMock()
        transport.handle_message = async_mock.CoroutineMock()
        transport.wire_format.encode_message = async_mock.CoroutineMock()
        transport.start = async_mock.CoroutineMock()
        transport.stop = async_mock.CoroutineMock()
        transport.schemes = ["http"]

        transport_cls = async_mock.MagicMock()
        transport_cls.schemes = ["http"]
        transport_cls.return_value = transport
        mgr.register_class(transport_cls, "transport_cls")
        assert mgr.get_registered_transport_for_scheme("http") == "transport_cls"

        await mgr.start()
        await mgr.task_queue
        transport.start.assert_awaited_once_with()
        assert mgr.get_running_transport_for_scheme("http") == "transport_cls"

        message = OutboundMessage(payload="{}")
        message.target = ConnectionTarget(
            endpoint="http://localhost",
            recipient_keys=[1, 2],
            routing_keys=[3],
            sender_key=4,
        )

        mgr.enqueue_message(context, message)
        await mgr.flush()
        transport.wire_format.encode_message.assert_awaited_once_with(
            context,
            message.payload,
            message.target.recipient_keys,
            message.target.routing_keys,
            message.target.sender_key,
        )
        transport.handle_message.assert_awaited_once_with(
            transport.wire_format.encode_message.return_value, message.target.endpoint
        )
        await mgr.stop()

        assert mgr.get_running_transport_for_scheme("http") is None
        transport.stop.assert_awaited_once_with()
