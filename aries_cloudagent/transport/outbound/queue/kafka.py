"""Kafka outbound transport."""
import logging
import msgpack

from aiokafka import AIOKafkaProducer
from random import randrange
from typing import Union

from ....core.profile import Profile
from .base import BaseOutboundQueue, OutboundQueueConfigurationError, OutboundQueueError


class KafkaOutboundQueue(BaseOutboundQueue):
    """Kafka outbound transport class."""

    config_key = "kafka_outbound_queue"

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
                "Configuration missing for kafka"
            ) from error

        self.prefix = self._profile.settings.get(
            "transport.outbound_queue_prefix"
        ) or config.get("prefix", "acapy")
        self.producer = None
        self.outbound_topic = f"{self.prefix}.outbound_transport"

    def __str__(self):
        """Return string representation of the outbound queue."""
        return f"KafkaOutboundQueue({self.prefix}, " f"{self.connection})"

    async def start(self):
        """Start the transport."""
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.connection,
            enable_idempotence=True,
        )
        await self.producer.start()

    async def stop(self):
        """Stop the transport."""
        await self.producer.stop()

    async def open(self):
        """Kafka connection context manager enter."""

    async def close(self):
        """Kafka connection context manager exit."""
        if self.producer._closed:
            await self.producer.start()

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
        await self.producer.send(
            self.outbound_topic,
            value=message,
            key=(f"{self.outbound_topic}_{str(randrange(5))}".encode("utf-8")),
        )
