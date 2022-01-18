import asyncio
import msgpack
import sys

from aiohttp import WSMessage, WSMsgType, web
from aiokafka import AIOKafkaProducer
from uuid import uuid4


def log_error(*args):
    print(*args, file=sys.stderr)


class KafkaHTTPHandler:
    def __init__(self, host: str, prefix: str, site_host: str, site_port: str):
        self._host = host
        self.prefix = prefix
        self.site_host = site_host
        self.site_port = site_port
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self._host, transactional_id=str(uuid4())
        )

    async def run(self):
        """Construct the aiohttp application."""
        await self.producer.start()
        app = web.Application()
        app.add_routes([web.get("/", self.message_handler)])
        app.add_routes([web.post("/", self.invite_handler)])
        runner = web.AppRunner(app)
        await runner.setup()
        self.site = web.TCPSite(runner, host=self.site_host, port=self.site_port)

    async def stop(self) -> None:
        """Shutdown."""
        if self.site:
            await self.site.stop()
            self.site = None

    async def invite_handler(self, request):
        """Handle inbound invitation."""
        if request.query.get("c_i"):
            return web.Response(
                text="You have received a connection invitation. To accept the "
                "invitation, paste it into your agent application."
            )
        else:
            return web.Response(status=200)

    async def message_handler(self, request):
        """Message handler for inbound messages."""
        ctype = request.headers.get("content-type", "")
        if ctype.split(";", 1)[0].lower() == "application/json":
            body = await request.text()
        else:
            body = await request.read()

            message = msgpack.packb(
                {"host": request.host, "remote": request.remote, "data": body}
            )
            key = f"{self.prefix}.inbound_transport"
            async with self.producer.transaction():
                await self.producer.send(
                    key,
                    value=message,
                    timestamp_ms=1000,
                )
            return web.Response(status=200)


class KafkaWSHandler:
    def __init__(self, host: str, prefix: str, site_host: str, site_port: str):
        self._host = host
        self.prefix = prefix
        self.site_host = site_host
        self.site_port = site_port
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self._host, transactional_id=str(uuid4())
        )

    async def run(self):
        """Construct the aiohttp application."""
        await self.producer.start()
        app = web.Application()
        app.add_routes([web.get("/", self.message_handler)])
        runner = web.AppRunner(app)
        await runner.setup()
        self.site = web.TCPSite(runner, host=self.site_host, port=self.site_port)

    async def stop(self) -> None:
        """Shutdown."""
        if self.site:
            await self.site.stop()
            self.site = None

    async def message_handler(self, request):
        """Message handler for inbound messages."""
        ws = web.WebSocketResponse(
            autoping=True,
            heartbeat=3,
            receive_timeout=15,
        )
        await ws.prepare(request)
        loop = asyncio.get_event_loop()
        inbound = loop.create_task(ws.receive())

        while not ws.closed:
            await inbound

            if inbound.done():
                msg: WSMessage = inbound.result()
                if msg.type in (WSMsgType.TEXT, WSMsgType.BINARY):
                    message = msgpack.packb(
                        {
                            "host": request.host,
                            "remote": request.remote,
                            "data": msg.data,
                        }
                    )
                    key = f"{self.prefix}.inbound_transport"
                    async with self.producer.transaction():
                        await self.producer.send(
                            key,
                            value=message,
                            timestamp_ms=1000,
                        )
                elif msg.type == WSMsgType.ERROR:
                    log_error(
                        "Websocket connection closed with exception: %s",
                        ws.exception(),
                    )
                else:
                    log_error(
                        "Unexpected Websocket message type received: %s: %s, %s",
                        msg.type,
                        msg.data,
                        msg.extra,
                    )
                if not ws.closed:
                    inbound = loop.create_task(ws.receive())

        if inbound and not inbound.done():
            inbound.cancel()

        if not ws.closed:
            await ws.close()
        log_error("Websocket connection closed")

        return ws


async def main(
    host: str, prefix: str, wire_format: str, site_host: str, site_port: str
):
    if wire_format == "ws":
        handler = KafkaWSHandler(host, prefix, site_host, site_port)
    elif wire_format == "http":
        handler = KafkaHTTPHandler(host, prefix, site_host, site_port)
    else:
        raise SystemExit("Only ws and http transport type are supported.")
    try:
        await handler.run()
    finally:
        await handler.stop()


if __name__ == "__main__":
    args = sys.argv
    if len(args) <= 1:
        raise SystemExit("Pass Kafka host URL as the first parameter")
    if len(args) > 6:
        raise SystemExit(
            "More than 6 parameters found, only kafka_host,"
            " topic_prefix, site_transport_type, site_host, site_port"
        )

    asyncio.get_event_loop().run_until_complete(
        main(args[1], args[2], args[3], args[4], args[5])
    )
