import json
import socket
from typing import Callable

from . import BaseTransport

from aiohttp import web


class InvalidMessageError(Exception):
    pass


class HttpSetupError(Exception):
    pass


class Http(BaseTransport):
    def __init__(self, host: str, port: int, message_router: Callable) -> None:
        self.host = host
        self.port = port
        self.message_router = message_router

    async def start(self) -> None:
        app = web.Application()
        app.add_routes([web.post("/", self.message_handler)])
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host=self.host, port=self.port)
        try:
            await site.start()
            # web.run_app(app, host=self.host, port=self.port, print=None)
        except OSError:
            raise HttpSetupError(
                f"Unable to start webserver with host '{self.host}' and port '{self.port}'\n"
            )

    async def parse_message(self, request):
        try:
            body = await request.json()
        except json.JSONDecodeError:
            raise InvalidMessageError(
                "Request body must contain a valid application/json payload"
            )
        return body

    async def message_handler(self, request):
        body = await self.parse_message(request)

        try:
            self.message_router(body)
        except Exception as e:
            return web.Response(text=str(e), status=400)

        return web.Response(text="OK", status=200)
