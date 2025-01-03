"""Message type identifiers for Trust Pings."""

# from ...didcomm_prefix import DIDCommPrefix
import logging
from ....messaging.v2_agent_message import V2AgentMessage
from ....connections.models.connection_target import ConnectionTarget
from didcomm_messaging import DIDCommMessaging, RoutingService

SPEC_URI = "https://identity.foundation/didcomm-messaging/spec/v2.1/#the-empty-message"

# Message types
EMPTY = "https://didcomm.org/empty/1.0/empty"

PROTOCOL_PACKAGE = "acapy_agent.protocols_v2.empty.v1_0"


class basic_message:
    async def __call__(self, *args, **kwargs):
        await self.handle(*args, **kwargs)

    @staticmethod
    async def handle(context, responder, payload):
        logger = logging.getLogger(__name__)
        logger.trace("Received empty message")


HANDLERS = {
    EMPTY: f"{PROTOCOL_PACKAGE}.message_types.empty",
}.items()

MESSAGE_TYPES = {
    EMPTY: f"{PROTOCOL_PACKAGE}.message_types.empty",
}
