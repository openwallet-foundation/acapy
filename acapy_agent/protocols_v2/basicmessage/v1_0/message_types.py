"""Message type identifiers for Trust Pings."""

# from ...didcomm_prefix import DIDCommPrefix
import logging
from ....messaging.v2_agent_message import V2AgentMessage
from ....connections.models.connection_target import ConnectionTarget
from didcomm_messaging import DIDCommMessaging, RoutingService

SPEC_URI = "https://didcomm.org/basicmessage/2.0/message"

# Message types
BASIC_MESSAGE = "https://didcomm.org/basicmessage/2.0/message"

PROTOCOL_PACKAGE = "acapy_agent.protocols_v2.basicmessage.v1_0"


class basic_message:
    async def __call__(self, *args, **kwargs):
        await self.handle(*args, **kwargs)

    @staticmethod
    async def handle(context, responder, payload):
        logger = logging.getLogger(__name__)
        their_did = context.message_receipt.sender_verkey.split("#")[0]
        our_did = context.message_receipt.recipient_verkey.split("#")[0]
        error_result = V2AgentMessage(
            message={
                "type": BASIC_MESSAGE,
                "body": {
                    "content": "Hello from acapy",
                },
                "to": [their_did],
                "from": our_did,
                "lang": "en",
            }
        )
        await responder.send_reply(error_result)


HANDLERS = {
    BASIC_MESSAGE: f"{PROTOCOL_PACKAGE}.message_types.basic_message",
}.items()

MESSAGE_TYPES = {
    BASIC_MESSAGE: f"{PROTOCOL_PACKAGE}.message_types.basic_message",
}
