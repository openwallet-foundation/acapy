import asyncio
import json

from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop, unused_port
from aiohttp import web
from asynctest import mock as async_mock

from ..http import HttpTransport
from ..message import InboundMessage
from ..receipt import MessageReceipt


class TestHttpTransport(AioHTTPTestCase):
    def setUp(self):
        self.message_results = []
        self.port = unused_port()
        self.receipt = None
        self.session = None
        self.transport = None
        super(TestHttpTransport, self).setUp()

    def get_transport(self):
        if not self.transport:
            self.transport = HttpTransport("0.0.0.0", self.port, self.create_session)
        return self.transport

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

    async def receive_message(self, payload):
        self.message_results.append([json.loads(payload)])
        return InboundMessage(payload, self.receipt)
        # single_response.set_result('{"response": "ok"}')

    def get_application(self):
        return self.get_transport().make_application()

    @unittest_run_loop
    async def test_send_message(self):
        await self.transport.start()

        test_message = {"test": "message"}
        self.receipt = MessageReceipt()
        resp = await self.client.post("/", json=test_message)

        assert self.session
        assert self.session.scheme == "http"
        assert self.message_results == [[test_message]]
        # assert await resp.json() == {"response": "ok"}

        await self.transport.stop()
