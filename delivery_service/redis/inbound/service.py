"""Redis Inbound Delivery Service."""
import aioredis
import asyncio
import argparse
import msgpack
import sys
import json
import yaml

from aiohttp import WSMessage, WSMsgType, web
from uuid import uuid4


def log_error(*args):
    """Print log error."""
    print(*args, file=sys.stderr)


class RedisHTTPHandler:
    """Redis inbound delivery service for HTTP."""

    def __init__(self, host: str, prefix: str, site_host: str, site_port: str):
        """Initialize KafkaHTTPHandler."""
        self._host = host
        self.prefix = prefix
        self.site_host = site_host
        self.site_port = site_port
        self._pool = None
        self.redis = None
        self.direct_response_txn_request_map = {}
        self.direct_resp_topic = f"{self.prefix}.inbound_direct_responses"
        self.inbound_transport_key = f"{self.prefix}.inbound_transport"

    async def run(self):
        """Run the service."""
        self._pool = aioredis.ConnectionPool.from_url(self._host, max_connections=10)
        self.redis = aioredis.Redis(connection_pool=self._pool)
        await asyncio.gather(self.start(), self.process_direct_responses())

    async def start(self):
        """Construct the aiohttp application."""
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

    async def process_direct_responses(self):
        """Process inbound_direct_responses and update direct_response_txn_request_map."""
        while True:
            try:
                msg = await self.redis.blpop(self.direct_resp_topic, 0)
            except aioredis.RedisError as err:
                log_error(f"Unexpected redis client exception, {err}")
            msg = msgpack.unpackb(msg)
            if not isinstance(msg, dict):
                log_error("Received non-dict message")
            elif "response" not in msg:
                log_error("No response provided")
            elif "txn_id" not in msg:
                log_error("No txn_id provided")
            txn_id = msg["txn_id"]
            response_data = msg["response_data"]
            self.direct_response_txn_request_map[txn_id] = response_data
            await asyncio.sleep(1)

    async def get_direct_responses(self, txn_id):
        """Get direct_response for a specific transaction/request."""
        while True:
            if txn_id in self.direct_response_txn_request_map:
                return self.direct_response_txn_request_map[txn_id]
            await asyncio.sleep(1)

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
        message_dict = json.loads(body)
        direct_response_request = False
        transport_dec = message_dict.get("~transport")
        if transport_dec:
            direct_response_mode = transport_dec.get("return_route")
            if direct_response_mode and direct_response_mode != "none":
                direct_response_request = True
        txn_id = str(uuid4())
        if direct_response_request:
            self.direct_response_txn_request_map[txn_id] = request
            message = msgpack.packb(
                {
                    "host": request.host,
                    "remote": request.remote,
                    "data": body.encode("utf-8"),
                    "txn_id": txn_id,
                    "transport_type": "http",
                }
            )
            try:
                return await self.redis.rpush(self.inbound_transport_key, message)
            except aioredis.RedisError as err:
                log_error(f"Unexpected redis client exception, {err}")
            try:
                response_data = await asyncio.wait_for(
                    self.get_direct_responses(
                        txn_id=txn_id,
                    ),
                    15,
                )
                response = response_data["response"].decode("utf-8")
                content_type = (
                    response_data["content_type"]
                    if "content_type" in response_data
                    else "application/json"
                )
                if response:
                    return web.Response(
                        text=response,
                        status=200,
                        headers={"Content-Type": content_type},
                    )
            except asyncio.TimeoutError:
                return web.Response(status=200)
        else:
            message = msgpack.packb(
                {
                    "host": request.host,
                    "remote": request.remote,
                    "data": body.encode("utf-8"),
                }
            )
            try:
                return await self.redis.rpush(self.inbound_transport_key, message)
            except aioredis.RedisError as err:
                log_error(f"Unexpected redis client exception, {err}")
            return web.Response(status=200)


class RedisWSHandler:
    """Redis inbound delivery service for WebSockets."""

    def __init__(self, host: str, prefix: str, site_host: str, site_port: str):
        """Initialize KafkaHTTPHandler."""
        self._host = host
        self.prefix = prefix
        self.site_host = site_host
        self.site_port = site_port
        self._pool = None
        self.redis = None
        self.direct_response_txn_request_map = {}
        self.direct_resp_topic = f"{self.prefix}.inbound_direct_responses"
        self.inbound_transport_key = f"{self.prefix}.inbound_transport"

    async def run(self):
        """Run the service."""
        self._pool = aioredis.ConnectionPool.from_url(self._host, max_connections=10)
        self.redis = aioredis.Redis(connection_pool=self._pool)
        await asyncio.gather(self.start(), self.process_direct_responses())

    async def start(self):
        """Construct the aiohttp application."""
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

    async def process_direct_responses(self):
        """Process inbound_direct_responses and update direct_response_txn_request_map."""
        while True:
            try:
                msg = await self.redis.blpop(self.direct_resp_topic, 0)
            except aioredis.RedisError as err:
                log_error(f"Unexpected redis client exception, {err}")
            msg = msgpack.unpackb(msg)
            if not isinstance(msg, dict):
                log_error("Received non-dict message")
            elif "response" not in msg:
                log_error("No response provided")
            elif "txn_id" not in msg:
                log_error("No txn_id provided")
            txn_id = msg["txn_id"]
            response_data = msg["response_data"]
            self.direct_response_txn_request_map[txn_id] = response_data
            await asyncio.sleep(2)

    async def get_direct_responses(self, txn_id):
        """Get direct_response for a specific transaction/request."""
        while True:
            if txn_id in self.direct_response_txn_request_map:
                return self.direct_response_txn_request_map[txn_id]
            await asyncio.sleep(1)

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
                    message_dict = json.loads(msg.data)
                    direct_response_request = False
                    transport_dec = message_dict.get("~transport")
                    if transport_dec:
                        direct_response_mode = transport_dec.get("return_route")
                        if direct_response_mode and direct_response_mode != "none":
                            direct_response_request = True
                    txn_id = str(uuid4())
                    if direct_response_request:
                        self.direct_response_txn_request_map[txn_id] = request
                        message = msgpack.packb(
                            {
                                "host": request.host,
                                "remote": request.remote,
                                "data": msg.data.encode("utf-8"),
                                "txn_id": txn_id,
                                "transport_type": "ws",
                            }
                        )
                        try:
                            return await self.redis.rpush(
                                self.inbound_transport_key, message
                            )
                        except aioredis.RedisError as err:
                            log_error(f"Unexpected redis client exception, {err}")
                        try:
                            response_data = await asyncio.wait_for(
                                self.get_direct_responses(
                                    txn_id=txn_id,
                                ),
                                15,
                            )
                            response = response_data["response"].decode("utf-8")
                            if response:
                                if isinstance(response, bytes):
                                    await ws.send_bytes(response)
                                else:
                                    await ws.send_str(response)
                        except asyncio.TimeoutError:
                            pass
                    else:
                        message = msgpack.packb(
                            {
                                "host": request.host,
                                "remote": request.remote,
                                "data": msg.data.encode("utf-8"),
                            }
                        )
                        try:
                            return await self.redis.rpush(
                                self.inbound_transport_key, message
                            )
                        except aioredis.RedisError as err:
                            log_error(f"Unexpected redis client exception, {err}")
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


async def main():
    """Start services."""
    parser = argparse.ArgumentParser(description="Redis Inbound Delivery Service.")
    parser.add_argument(
        "-iq",
        "--inbound-queue",
        dest="inbound_queue",
        type=str,
    )
    parser.add_argument(
        "-iqp",
        "--inbound-queue-prefix",
        dest="inbound_queue_prefix",
        type=str,
        default="acapy",
    )
    parser.add_argument(
        "-it",
        "--inbound-transports",
        dest="inbound_transports",
        type=str,
        action="append",
        nargs=3,
        metavar=("<module>", "<host>", "<port>"),
    )
    parser.add_argument(
        "--plugin-config",
        dest="plugin_config",
        type=str,
        required=False,
        help="Load YAML file path that defines external plugin configuration.",
    )
    args = parser.parse_args()
    config = None
    if args.plugin_config:
        with open(args.plugin_config, "r") as stream:
            loaded_plugin_config = yaml.safe_load(stream)
        config = loaded_plugin_config.get("redis_inbound_queue")
    if args.inbound_queue:
        host = args.inbound_queue
    elif config:
        host = config["connection"]
    else:
        raise SystemExit("No Redis host/connection provided.")
    if config:
        prefix = config.get("prefix", "acapy")
    elif args.inbound_queue_prefix:
        prefix = args.inbound_queue_prefix
    else:
        prefix = "acapy"
    tasks = []
    for inbound_transport in args.inbound_transports:
        transport_type, site_host, site_port = inbound_transport
        if transport_type == "ws":
            handler = RedisWSHandler(host, prefix, site_host, site_port)
        elif transport_type == "http":
            handler = RedisHTTPHandler(host, prefix, site_host, site_port)
        else:
            raise SystemExit("Only ws and http transport type are supported.")
        tasks.append(handler.run())
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
