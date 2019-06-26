import asyncio

from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from aiohttp import web

from ....messaging.outbound_message import OutboundMessage

from ..http import HttpTransport
from ..queue.basic import BasicOutboundMessageQueue


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

        async def start_transport(transport):
            async with transport:
                await transport.start()

        async def do_send_message(transport, message):
            await transport.enqueue(message)
            await transport.stop()

        transport = HttpTransport(BasicOutboundMessageQueue())
        message = OutboundMessage("{}", endpoint=server_addr)
        await asyncio.wait_for(
            asyncio.gather(
                start_transport(transport), do_send_message(transport, message)
            ),
            5.0,
        )
        assert self.message_results == [{}]
