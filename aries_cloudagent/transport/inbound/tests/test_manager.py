import asyncio

from asynctest import TestCase as AsyncTestCase, mock as async_mock

from ....config.injection_context import InjectionContext

from ..base import InboundTransportConfiguration, InboundTransportRegistrationError
from ..manager import InboundTransportManager


# good_inbound_transports = {"transport.inbound_configs": [["http", "host", 80]]}
# good_outbound_transports = {"transport.outbound_configs": ["http"]}
# bad_inbound_transports = {"transport.inbound_configs": [["bad", "host", 80]]}
# bad_outbound_transports = {"transport.outbound_configs": ["bad"]}

#         mock_inbound_mgr.return_value.register.assert_called_once_with(
#             InboundTransportConfiguration(module="http", host="host", port=80),
#             conductor.inbound_message_router,
#         )


class TestInboundTransportManager(AsyncTestCase):
    def test_register_path(self):
        context = InjectionContext()
        mgr = InboundTransportManager(context, None)

        config = InboundTransportConfiguration(module="http", host="0.0.0.0", port=80)
        mgr.register(config)

        config = InboundTransportConfiguration(
            module="notransport", host="0.0.0.0", port=80
        )
        with self.assertRaises(InboundTransportRegistrationError):
            mgr.register(config)

    async def test_start_stop(self):
        transport = async_mock.MagicMock()
        transport.start = async_mock.CoroutineMock()
        transport.stop = async_mock.CoroutineMock()

        context = InjectionContext()
        mgr = InboundTransportManager(context, None)
        mgr.register_transport(transport, "transport_cls")
        await mgr.start()
        await mgr.task_queue
        transport.start.assert_awaited_once_with()
        assert mgr.get_transport_instance("transport_cls") is transport

        await mgr.stop()
        transport.stop.assert_awaited_once_with()
