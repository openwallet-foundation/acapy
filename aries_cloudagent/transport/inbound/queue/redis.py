"""Redis inbound transport."""
import asyncio
import aioredis
import msgpack
import logging

from threading import Thread

from ....core.profile import Profile
from .base import BaseInboundQueue, InboundQueueConfigurationError, InboundQueueError


class RedisInboundQueue(BaseInboundQueue, Thread):
    """Redis outbound transport class."""

    config_key = "redis_inbound_queue"

    def __init__(self, root_profile: Profile) -> None:
        """Set initial state."""
        self._logger = logging.getLogger(__name__)
        try:
            plugin_config = root_profile.settings["plugin_config"] or {}
            config = plugin_config[self.config_key]
            self.connection = config["connection"]
        except KeyError as error:
            raise InboundQueueConfigurationError(
                "Configuration missing for redis queue"
            ) from error

        self.prefix = config.get("prefix", "acapy")
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

    async def recieve_messages(
        self,
    ):
        """Recieve message from inbound queue and handle it."""
        topic = f"{self.prefix}.inbound_transport"
        while True:
            try:
                msg = await self.redis.blpop(topic, 0)
            except aioredis.RedisError as error:
                raise InboundQueueError("Unexpected redis client exception") from error
            msg = msgpack.unpackb(msg)
            if not isinstance(msg, dict):
                self._logger.error("Received non-dict message")
                continue
            elif "transport_type" not in msg and msg["transport_type"] not in [
                "http",
                "ws",
            ]:
                self._logger.error(
                    "Received message with invalid transport type specified"
                )
                continue
            client_info = {"host": msg["host"], "remote": msg["remote"]}
            session = await self.create_session(
                accept_undelivered=True, can_respond=True, client_info=client_info
            )
            async with session:
                if msg["transport_type"] == "ws":
                    await session.receive(msg["data"])
                elif msg["transport_type"] == "http":
                    await session.receive(msg["body"])
