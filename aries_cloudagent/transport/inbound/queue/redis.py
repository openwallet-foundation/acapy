"""Redis inbound transport."""
import aioredis
import msgpack
import logging

from threading import Thread

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
        self.pool = aioredis.ConnectionPool.from_url(
            self.connection, max_connections=10
        )
        self.redis = aioredis.Redis(connection_pool=self.pool)

    def __str__(self):
        """Return string representation of the outbound queue."""
        return (
            f"RedisInboundQueue("
            f"connection={self.connection}, "
            f"prefix={self.prefix}"
            f")"
        )

    async def start(self):
        """Start the transport."""
        # aioredis will lazily connect but we can eagerly trigger connection with:
        # await self.redis.ping()
        # Calling this on enter to `async with` just before another queue
        # operation is made does not make sense and we should just let aioredis
        # do lazy connection.

    async def stop(self):
        """Stop the transport."""
        # aioredis cleans up automatically but we can clean up manually with:
        # await self.pool.disconnect()
        # However, calling this on exit of `async with` does not make sense and
        # we should just let aioredis handle the connection lifecycle.

    async def receive_messages(
        self,
    ):
        """Recieve message from inbound queue and handle it."""
        inbound_topic = f"{self.prefix}.inbound_transport"
        direct_response_topic = f"{self.prefix}.inbound_direct_responses"
        transport_manager = self._profile.context.injector.inject(
            InboundTransportManager
        )
        while self.RUNNING:
            try:
                msg = await self.redis.blpop(inbound_topic, 0)
            except aioredis.RedisError as error:
                raise InboundQueueError("Unexpected redis client exception") from error
            msg = msgpack.unpackb(msg)
            if not isinstance(msg, dict):
                self.logger.error("Received non-dict message")
                continue
            client_info = {"host": msg["host"], "remote": msg["remote"]}
            session = await transport_manager.create_session(
                accept_undelivered=True, can_respond=True, client_info=client_info
            )
            direct_reponse_requested = True if "txn_id" in msg else False
            async with session:
                await session.receive(msg["data"])
                if direct_reponse_requested:
                    txn_id = msg["txn_id"]
                    transport_type = msg["transport_type"]
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
                            direct_response_topic, msgpack.dumps(message)
                        )
                    except aioredis.RedisError as error:
                        raise InboundQueueError(
                            "Unexpected redis client exception"
                        ) from error
