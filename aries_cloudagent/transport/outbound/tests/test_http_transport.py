import asyncio

from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from aiohttp import web

from ....stats import Collector

from ...outbound.message import OutboundMessage

from ..http import HttpTransport


class TestHttpTransport(AioHTTPTestCase):
    async def setUpAsync(self):
        self.message_results = []

    async def receive_message(self, request):
        payload = await request.json()
        self.message_results.append(payload)
        raise web.HTTPOk()

    async def get_application(self):
        """
        Override the get_app method to return your application.
        """
        app = web.Application()
        app.add_routes([web.post("/", self.receive_message)])
        return app

    @unittest_run_loop
    async def test_handle_message(self):
        server_addr = f"http://localhost:{self.server.port}"

        async def send_message(transport, payload, endpoint):
            async with transport:
                await transport.handle_message(payload, endpoint)

        transport = HttpTransport()
        await asyncio.wait_for(send_message(transport, "{}", endpoint=server_addr), 5.0)
        assert self.message_results == [{}]

    @unittest_run_loop
    async def test_stats(self):
        server_addr = f"http://localhost:{self.server.port}"

        async def send_message(transport, payload, endpoint):
            async with transport:
                await transport.handle_message(payload, endpoint)

        transport = HttpTransport()
        transport.collector = Collector()
        await asyncio.wait_for(
            send_message(transport, b"{}", endpoint=server_addr), 5.0
        )

        results = transport.collector.extract()
        assert results["count"] == {
            "outbound-http:dns_resolve": 1,
            "outbound-http:connect": 1,
            "outbound-http:POST": 1,
        }
