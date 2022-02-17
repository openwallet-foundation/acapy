"""Redis inbound transport."""
import aioredis
import asyncio
import msgpack
import logging

from threading import Thread
from urllib.parse import urlparse, ParseResult

from ....core.profile import Profile

from ...wire_format import DIDCOMM_V0_MIME_TYPE, DIDCOMM_V1_MIME_TYPE

from ..manager import InboundTransportManager

from .base import BaseInboundQueue, InboundQueueConfigurationError, InboundQueueError


class RedisInboundQueue(BaseInboundQueue, Thread):
    """Redis outbound transport class."""

    config_key = "redis_inbound_queue"
    # for unit testing
    RUNNING = True

    def __init__(self, root_profile: Profile) -> None:
        """Set initial state."""
        Thread.__init__(self)
        self._profile = root_profile
        self.logger = logging.getLogger(__name__)
        try:
            plugin_config = root_profile.settings.get("plugin_config", {})
            config = plugin_config.get(self.config_key, {})
            self.connection = (
                self._profile.settings.get("transport.inbound_queue")
                or config["connection"]
            )
        except KeyError as error:
            raise InboundQueueConfigurationError(
                "Configuration missing for redis queue"
            ) from error

        self.prefix = self._profile.settings.get(
            "transport.inbound_queue_prefix"
        ) or config.get("prefix", "acapy")
        self.redis = None
        self.inbound_topic = f"{self.prefix}.inbound_transport"
        self.direct_response_topic = f"{self.prefix}.inbound_direct_responses"
        self.listener_config = self._profile.settings.get(
            "transport.inbound_queue_transports", []
        )
        self.listener_urls = []
        for transport in self.listener_config:
            module, host, port = transport
            self.listener_urls.append(f"{module}://{host}:{port}")

    def __str__(self):
        """Return string representation of the outbound queue."""
        return (
            f"RedisInboundQueue(prefix={self.prefix}, " f"connection={self.connection})"
        )

    def sanitize_connection_url(self) -> str:
        """Return sanitized connection with no secrets included."""
        parsed: ParseResult = urlparse(self.connection)
        if parsed.username or parsed.password:
            sanitized = self.connection.rsplit("@", 1)[1]
            return f"{parsed.scheme}://{sanitized}"
        else:
            return self.connection

    async def start_queue(self):
        """Start the transport."""
        self.daemon = True
        self.start()
        loop = asyncio.get_event_loop()
        asyncio.ensure_future(self.receive_messages(), loop=loop)

    async def stop_queue(self):
        """Stop the transport."""

    async def receive_messages(self):
        """Recieve message from inbound queue and handle it."""
        self.redis = aioredis.from_url(self.connection)
        transport_manager = self._profile.context.injector.inject(
            InboundTransportManager
        )
        while self.RUNNING:
            msg_received = False
            retry_pop_count = 0
            while not msg_received:
                try:
                    msg = await self.redis.blpop(self.inbound_topic, 0)
                    msg_received = True
                    retry_pop_count = 0
                except aioredis.RedisError as err:
                    await asyncio.sleep(1)
                    self.logger.warning(err)
                    retry_pop_count = retry_pop_count + 1
                    if retry_pop_count > 5:
                        raise InboundQueueError(f"Unexpected exception {str(err)}")
            msg = msgpack.unpackb(msg[1])
            if not isinstance(msg, dict):
                self.logger.error("Received non-dict message")
                continue
            client_info = {"host": msg["host"], "remote": msg["remote"]}
            transport_type = msg.get("transport_type")
            session = await transport_manager.create_session(
                transport_type=transport_type,
                accept_undelivered=True,
                can_respond=True,
                client_info=client_info,
            )
            direct_reponse_requested = True if "txn_id" in msg else False
            async with session:
                await session.receive(msg["data"].encode("utf-8"))
                if direct_reponse_requested:
                    txn_id = msg["txn_id"]
                    response = await session.wait_response()
                    response_data = {}
                    if transport_type == "http" and response:
                        if isinstance(response, bytes):
                            if session.profile.settings.get(
                                "emit_new_didcomm_mime_type"
                            ):
                                response_data["content-type"] = DIDCOMM_V1_MIME_TYPE
                            else:
                                response_data["content-type"] = DIDCOMM_V0_MIME_TYPE
                        else:
                            response_data["content-type"] = "application/json"
                    response_data["response"] = response
                    message = {}
                    message["txn_id"] = txn_id
                    message["response_data"] = response_data
                    try:
                        await self.redis.rpush(
                            self.direct_response_topic, msgpack.packb(message)
                        )
                    except aioredis.RedisError as err:
                        raise InboundQueueError(f"Unexpected exception {str(err)}")
