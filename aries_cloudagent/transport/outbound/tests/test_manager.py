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

        message = OutboundMessage(payload=None, enc_payload="")
        message.target = ConnectionTarget(endpoint="http://localhost")

        mgr.enqueue_message(context, message)
        await mgr.task_queue
        await mgr.stop()
        transport.handle_message.assert_called_once_with(
            message.enc_payload, message.target.endpoint
        )

        assert mgr.get_running_transport_for_scheme("http") is None
        transport.stop.assert_called_once_with()
