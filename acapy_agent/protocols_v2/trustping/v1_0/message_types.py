"""Message type identifiers for Trust Pings."""

#from ...didcomm_prefix import DIDCommPrefix
import logging
from ....messaging.v2_agent_message import V2AgentMessage

SPEC_URI = (
    "https://github.com/hyperledger/aries-rfcs/tree/"
    "527849ec3aa2a8fd47a7bb6c57f918ff8bcb5e8c/features/0048-trust-ping"
)

# Message types
PING = "trust_ping/1.0/ping"
PING_RESPONSE = "trust_ping/1.0/ping_response"
DEBUG = "https://didcomm.org/basicmessage/2.0/message"

PROTOCOL_PACKAGE = "acapy_agent.protocols_v2.trustping.v1_0"

class test_func:
    async def __call__(self, *args, **kwargs):
        await self.handle(*args, **kwargs)
    @staticmethod
    async def handle(context, responder, payload):
        message = payload
        logger = logging.getLogger(__name__)
        error_result = V2AgentMessage(
            message={
                "type": "https://didcomm.org/basicmessage/2.0/message",
                "body": {
                    "message": "Hello Frosty :3",
                },
            }
        )
        await responder.send_reply(error_result)

HANDLERS = {
    DEBUG: f"{PROTOCOL_PACKAGE}.message_types.test_func",
}.items()

MESSAGE_TYPES = {
        DEBUG: f"{PROTOCOL_PACKAGE}.message_types.test_func",
}
