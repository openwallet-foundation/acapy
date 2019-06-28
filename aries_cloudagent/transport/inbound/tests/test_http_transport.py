import asyncio
import json

from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop, unused_port
from aiohttp import web

from ..http import HttpTransport


class TestHttpTransport(AioHTTPTestCase):
    def setUp(self):
        self.message_results = []
        self.port = unused_port()
        self.transport = None
        super(TestHttpTransport, self).setUp()

    def get_transport(self):
        if not self.transport:
            self.transport = HttpTransport(
                "0.0.0.0", self.port, self.receive_message, None
            )
        return self.transport

    def get_application(self):
        return self.get_transport().make_application()

    async def receive_message(self, payload, scheme, single_response=None):
        self.message_results.append([json.loads(payload), scheme])
        if single_response:
            single_response.set_result('{"response": "ok"}')

    @unittest_run_loop
    async def test_send_message(self):
        await self.transport.start()

        test_message = {"test": "message"}
        resp = await self.client.post("/", json=test_message)

        assert self.message_results == [[test_message, "http"]]
        assert await resp.json() == {"response": "ok"}

        await self.transport.stop()
