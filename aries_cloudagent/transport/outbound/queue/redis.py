"""Redis outbound transport."""
import asyncio
import logging
import msgpack

from redis.cluster import RedisCluster as Redis
from redis.exceptions import RedisError
from typing import Union
from urllib.parse import urlparse, ParseResult

from ....core.profile import Profile

from .base import BaseOutboundQueue, OutboundQueueConfigurationError, OutboundQueueError


class RedisOutboundQueue(BaseOutboundQueue):
    """Redis outbound transport class."""

    config_key = "redis_outbound_queue"

    def __init__(self, root_profile: Profile) -> None:
        """Set initial state."""
        self._profile = root_profile
        self.logger = logging.getLogger(__name__)
        try:
            plugin_config = root_profile.settings.get("plugin_config", {})
            config = plugin_config.get(self.config_key, {})
            self.connection = (
                self._profile.settings.get("transport.outbound_queue")
                or config["connection"]
            )
        except KeyError as error:
            raise OutboundQueueConfigurationError(
                "Configuration missing for redis queue"
            ) from error

        self.prefix = self._profile.settings.get(
            "transport.outbound_queue_prefix"
        ) or config.get("prefix", "acapy")
        self.redis = None
        self.outbound_topic = f"{self.prefix}.outbound_transport"

    def __str__(self):
        """Return string representation of the outbound queue."""
        return (
            f"RedisOutboundQueue(prefix={self.prefix}, "
            f"connection={self.connection})"
        )

    def sanitize_connection_url(self) -> str:
        """Return sanitized connection with no secrets included."""
        parsed: ParseResult = urlparse(self.connection)
        if parsed.username or parsed.password:
            sanitized = self.connection.rsplit("@", 1)[1]
            return f"{parsed.scheme}://{sanitized}"
        else:
            return self.connection

    async def start(self):
        """Start the transport."""
        self.redis = Redis.from_url(self.connection)
        self.redis.ping()

    async def stop(self):
        """Stop the transport."""

    async def push(self, key: str, message: bytes):
        """Push a ``message`` to redis on ``key``."""
        try:
            self.redis.rpush(key, message)
        except RedisError as err:
            raise OutboundQueueError(f"Unexpected exception {str(err)}")

    async def enqueue_message(
        self,
        payload: Union[str, bytes],
        endpoint: str,
    ):
        """Prepare and send message to external redis.

        Args:
            payload: message payload in string or byte format
            endpoint: URI endpoint for delivery
        """
        if not endpoint:
            raise OutboundQueueError("No endpoint provided")
        if isinstance(payload, bytes):
            content_type = "application/ssi-agent-wire"
        else:
            content_type = "application/json"
        message = msgpack.packb(
            {
                "headers": {"Content-Type": content_type},
                "endpoint": endpoint,
                "payload": payload,
            }
        )
        message_sent = False
        while not message_sent:
            try:
                await self.push(self.outbound_topic, message)
                message_sent = True
            except OutboundQueueError as err:
                await asyncio.sleep(1)
                self.logger.warning(f"Resetting Redis connection pool, {str(err)}")
                self.redis = Redis.from_url(self.connection)
                self.redis.ping()
