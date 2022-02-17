"""Kafka outbound transport."""
import logging
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
        (self.connection, self.username, self.password) = self.parse_connection_url(
            self.connection
        )
        self.prefix = self._profile.settings.get(
            "transport.outbound_queue_prefix"
        ) or config.get("prefix", "acapy")
        self.producer = None
        self.outbound_topic = f"{self.prefix}.outbound_transport"

    def __str__(self):
        """Return string representation of the outbound queue."""
        return f"KafkaOutboundQueue({self.prefix}, " f"{self.connection})"

    def parse_connection_url(self, connection):
        """Retreive bootstrap_server, username and password from provided connection."""
        kafka_username = None
        kafka_password = None
        split_kafka_url_by_hash = connection.rsplit("#", 1)
        if len(split_kafka_url_by_hash) > 1:
            kafka_username = split_kafka_url_by_hash[1].split(":")[0]
            kafka_password = split_kafka_url_by_hash[1].split(":")[1]
        kafka_url = split_kafka_url_by_hash[0]
        return (kafka_url, kafka_username, kafka_password)

    def sanitize_connection_url(self) -> str:
        """Return sanitized connection with no secrets included."""
        return self.connection

    async def start(self):
        """Start the transport."""
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.connection,
            transactional_id=str(uuid4()),
            enable_idempotence=True,
            sasl_plain_username=self.username,
            sasl_plain_password=self.password,
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
        async with self.producer.transaction():
            await self.producer.send(
                self.outbound_topic,
                value=message,
            )
