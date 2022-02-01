"""Kafka outbound transport."""
import msgpack

from aiokafka import AIOKafkaProducer
from typing import Union
from uuid import uuid4

from ....core.profile import Profile
from .base import BaseOutboundQueue, OutboundQueueConfigurationError, OutboundQueueError


class KafkaOutboundQueue(BaseOutboundQueue):
    """Kafka outbound transport class."""

    config_key = "kafka_outbound_queue"

    def __init__(self, root_profile: Profile) -> None:
        """Set initial state."""
        self._profile = root_profile
        try:
            plugin_config = root_profile.settings.get("plugin_config", {})
            config = plugin_config.get(self.config_key, {})
            self.connection = (
                self._profile.settings.get("transport.outbound_queue")
                or config["connection"]
            )
            self.txn_id = config.get("transaction_id", str(uuid4()))
        except KeyError as error:
            raise OutboundQueueConfigurationError(
                "Configuration missing for kafka"
            ) from error

        self.prefix = self._profile.settings.get(
            "transport.outbound_queue_prefix"
        ) or config.get("prefix", "acapy")
        self.producer = None

    def __str__(self):
        """Return string representation of the outbound queue."""
        return (
            f"KafkaOutboundQueue({self.prefix}, "
            f"{self.connection})"
        )

    async def start(self):
        """Start the transport."""
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.connection, transactional_id=self.txn_id
        )
        await self.producer.start()

    async def stop(self):
        """Stop the transport."""
        await self.producer.stop()

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
        key = f"{self.prefix}.outbound_transport"
        async with self.producer.transaction():
            await self.producer.send(key, value=message, timestamp_ms=1000)
