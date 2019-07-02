import asyncio

from asynctest import TestCase as AsyncTestCase, mock as async_mock

from ....messaging.outbound_message import OutboundMessage

from ..manager import OutboundTransportManager, OutboundTransportRegistrationError
from ..queue.basic import BasicOutboundMessageQueue


class TestOutboundTransportManager(AsyncTestCase):
    def test_register_path(self):
        mgr = OutboundTransportManager()
        mgr.register("http")
        assert mgr.get_registered_transport_for_scheme("http")

        with self.assertRaises(OutboundTransportRegistrationError):
            mgr.register("http")

    async def test_send_message(self):
        mgr = OutboundTransportManager(BasicOutboundMessageQueue())

        transport_cls = async_mock.Mock(spec=[])
        with self.assertRaises(OutboundTransportRegistrationError):
            mgr.register_class(transport_cls)

        transport = async_mock.MagicMock()
        transport.handle_message = async_mock.CoroutineMock()
        transport.start = async_mock.CoroutineMock()
        transport.stop = async_mock.CoroutineMock()

        transport_cls = async_mock.MagicMock()
        transport_cls.schemes = ["http"]
        transport_cls.return_value = transport
        mgr.register_class(transport_cls)
        assert mgr.get_registered_transport_for_scheme("http") is transport_cls

        await mgr.start()
        await asyncio.sleep(0.1)
        transport.start.assert_called_once_with()
        assert mgr.get_running_transport_for_scheme("http") is transport

        message = OutboundMessage("")
        message.endpoint = "http://localhost"

        await mgr.send_message(message)
        await mgr.stop()
        transport.handle_message.assert_called_once_with(message)

        assert mgr.get_running_transport_for_scheme("http") is None
        transport.stop.assert_called_once_with()
