"""Message type identifiers for Trust Pings."""

#from ...didcomm_prefix import DIDCommPrefix
import logging
from ....messaging.v2_agent_message import V2AgentMessage
from ....connections.models.connection_target import ConnectionTarget
from didcomm_messaging import DIDCommMessaging, RoutingService

SPEC_URI = (
    "https://github.com/hyperledger/aries-rfcs/tree/"
    "527849ec3aa2a8fd47a7bb6c57f918ff8bcb5e8c/features/0048-trust-ping"
)

# Message types
PING = "trust_ping/1.0/ping"
PING_RESPONSE = "trust_ping/1.0/ping_response"
PING = "https://didcomm.org/trust-ping/2.0/ping"
BASIC_MESSAGE = "https://didcomm.org/basicmessage/2.0/message"
QUERIES = "https://didcomm.org/discover-features/2.0/queries"
DISCLOSE = "https://didcomm.org/discover-features/2.0/disclose"
EMPTY = "https://didcomm.org/empty/1.0/empty"

PROTOCOL_PACKAGE = "acapy_agent.protocols_v2.trustping.v1_0"

class trust_ping:
    async def __call__(self, *args, **kwargs):
        await self.handle(*args, **kwargs)
    @staticmethod
    async def handle(context, responder, payload):
        logger = logging.getLogger(__name__)
        if not payload["body"].get("response_requested", False):
            return
        their_did = context.message_receipt.sender_verkey.split('#')[0]
        our_did = context.message_receipt.recipient_verkey.split('#')[0]
        error_result = V2AgentMessage(
            message={
                "type": "https://didcomm.org/trust-ping/2.0/ping-response",
                "thid": payload["id"],
                "body": {},
                "to": [their_did],
                "from": our_did,
            }
        )
        await responder.send_reply(error_result)


class basic_message:
    async def __call__(self, *args, **kwargs):
        await self.handle(*args, **kwargs)
    @staticmethod
    async def handle(context, responder, payload):
        logger = logging.getLogger(__name__)
        their_did = context.message_receipt.sender_verkey.split('#')[0]
        our_did = context.message_receipt.recipient_verkey.split('#')[0]
        error_result = V2AgentMessage(
            message={
                "type": "https://didcomm.org/basicmessage/2.0/message",
                "body": {
                    "content": "Hello from acapy",
                },
                "to": [their_did],
                "from": our_did,
                "lang": "en",
            }
        )
        await responder.send_reply(error_result)


class discover_features:
    async def __call__(self, *args, **kwargs):
        await self.handle(*args, **kwargs)
    @staticmethod
    async def handle(context, responder, payload):
        logger = logging.getLogger(__name__)
        their_did = context.message_receipt.sender_verkey.split('#')[0]
        our_did = context.message_receipt.recipient_verkey.split('#')[0]
        error_result = V2AgentMessage(
            message={
                "type": DISCLOSE,
                "thid": payload["id"],
                "body": {
                    "disclosures": [
                        {
                            "feature-type": "protocol",
                            "id": protocol.rsplit("/", 1)[0],
                        }
                        for protocol in [PING, BASIC_MESSAGE, QUERIES, EMPTY]
                    ],
                },
                "to": [their_did],
                "from": our_did,
            }
        )
        await responder.send_reply(error_result)



HANDLERS = {
    PING: f"{PROTOCOL_PACKAGE}.message_types.trust_ping",
    BASIC_MESSAGE: f"{PROTOCOL_PACKAGE}.message_types.basic_message",
    QUERIES: f"{PROTOCOL_PACKAGE}.message_types.discover_features",
}.items()

MESSAGE_TYPES = {
        PING: f"{PROTOCOL_PACKAGE}.message_types.trust_ping",
        BASIC_MESSAGE: f"{PROTOCOL_PACKAGE}.message_types.basic_message",
        QUERIES: f"{PROTOCOL_PACKAGE}.message_types.discover_features",
}
