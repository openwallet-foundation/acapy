import asyncio
import json

from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from aiohttp import web, WSMsgType

from ....core.in_memory import InMemoryProfile

from ..ws import WsTransport


class TestWsTransport(AioHTTPTestCase):
    async def setUpAsync(self):
        self.profile = InMemoryProfile.test_profile()
        self.message_results = []
        await super().setUpAsync()

    async def receive_message(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        async for msg in ws:
            if msg.type in (WSMsgType.TEXT, WSMsgType.BINARY):
                self.message_results.append(json.loads(msg.data))

            elif msg.type == WSMsgType.ERROR:
                raise Exception(ws.exception())

        return ws

    async def get_application(self):
        """
        Override the get_app method to return your application.
        """
        app = web.Application()
        app.add_routes([web.get("/", self.receive_message)])
        return app

    async def test_handle_message(self):
        server_addr = f"ws://localhost:{self.server.port}"

        async def send_message(transport, payload, endpoint: str):
            async with transport:
                await transport.handle_message(self.profile, payload, endpoint)

        transport = WsTransport()
        await asyncio.wait_for(send_message(transport, "{}", endpoint=server_addr), 5.0)
        assert self.message_results == [{}]

        self.message_results.clear()
        await asyncio.wait_for(
            send_message(transport, b"{}", endpoint=server_addr), 5.0
        )
        assert self.message_results == [{}]
