import asyncio

from asynctest import TestCase as AsyncTestCase, mock as async_mock

from ..base import InboundTransportConfiguration, InboundTransportRegistrationError
from ..manager import InboundTransportManager


class TestInboundTransportManager(AsyncTestCase):
    def test_register_path(self):
        mgr = InboundTransportManager()

        config = InboundTransportConfiguration(module="http", host="0.0.0.0", port=80)
        mgr.register(config, None, None)

        config = InboundTransportConfiguration(
            module="notransport", host="0.0.0.0", port=80
        )
        with self.assertRaises(InboundTransportRegistrationError):
            mgr.register(config, None, None)

    async def test_start_stop(self):
        transport = async_mock.MagicMock()
        transport.start = async_mock.CoroutineMock()
        transport.stop = async_mock.CoroutineMock()

        mgr = InboundTransportManager()
        mgr.register_instance(transport)
        await mgr.start()
        transport.start.assert_called_once_with()

        await mgr.stop()
        transport.stop.assert_called_once_with()
