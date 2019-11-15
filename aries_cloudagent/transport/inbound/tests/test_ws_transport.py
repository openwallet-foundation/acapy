import asyncio
import json

from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop, unused_port
from aiohttp import web
from asynctest import mock as async_mock

from ..message import InboundMessage
from ..ws import WsTransport


class TestWsTransport(AioHTTPTestCase):
    def setUp(self):
        self.message_results = []
        self.port = unused_port()
        self.receipt = None
        self.session = None
        self.transport = WsTransport("0.0.0.0", self.port, self.create_session)
        super(TestWsTransport, self).setUp()

    def create_session(self, scheme, client_info, wire_format):
        if not self.session:
            session = async_mock.MagicMock()
            session.scheme, session.client_info, session.wire_format = (
                scheme,
                client_info,
                wire_format,
            )
            session.receive = self.receive_message
            self.session = session
        result = asyncio.Future()
        result.set_result(self.session)
        return result

    def get_application(self):
        return self.transport.make_application()

    async def receive_message(self, payload):
        self.message_results.append([json.loads(payload)])
        # if self.response_handler:
        #     await self.response_handler('{"response": "ok"}')
        # else:
        #     self.fail("no response handler")
        return InboundMessage(payload, self.receipt)

    @unittest_run_loop
    async def test_send_message(self):
        await self.transport.start()

        test_message = {"test": "message"}
        async with self.client.ws_connect("/") as ws:
            await ws.send_json(test_message)
            await asyncio.sleep(0.1)
            assert self.session
            # result = await asyncio.wait_for(ws.receive_json(), 1.0)
            # assert json.loads(result) == {"response": "ok"}

        assert self.message_results == [[test_message]]

        await self.transport.stop()

        # assert not self.response_handler
