import asyncio
import json

from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop, unused_port
from aiohttp import web

from ....messaging.socket import SocketRef
from ..ws import WsTransport


class TestWsTransport(AioHTTPTestCase):
    def setUp(self):
        self.message_results = []
        self.port = unused_port()
        self.response_handler = None
        self.socket_id = 99
        self.transport = WsTransport(
            "0.0.0.0", self.port, self.receive_message, self.register_socket
        )
        super(TestWsTransport, self).setUp()

    async def register_socket(self, handler):
        assert not self.response_handler
        self.response_handler = handler
        return SocketRef(self.socket_id, self.close_socket)

    async def close_socket(self):
        assert self.response_handler
        self.response_handler = None

    def get_application(self):
        return self.transport.make_application()

    async def receive_message(self, payload, scheme, socket_id):
        assert socket_id == self.socket_id
        self.message_results.append([json.loads(payload), scheme])
        if self.response_handler:
            await self.response_handler('{"response": "ok"}')
        else:
            self.fail("no response handler")

    @unittest_run_loop
    async def test_send_message(self):
        await self.transport.start()

        test_message = {"test": "message"}
        async with self.client.ws_connect("/") as ws:
            await ws.send_json(test_message)
            assert self.response_handler
            result = await asyncio.wait_for(ws.receive_json(), 5.0)
            assert json.loads(result) == {"response": "ok"}

        assert self.message_results == [[test_message, "ws"]]

        await self.transport.stop()

        assert not self.response_handler
