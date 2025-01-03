"""Message type identifiers for Trust Pings."""

# from ...didcomm_prefix import DIDCommPrefix
import logging
from ....messaging.v2_agent_message import V2AgentMessage
from ....connections.models.connection_target import ConnectionTarget
from didcomm_messaging import DIDCommMessaging, RoutingService

SPEC_URI = "https://didcomm.org/discover-features/2.0/queries"

# Message types
QUERIES = "https://didcomm.org/discover-features/2.0/queries"
DISCLOSE = "https://didcomm.org/discover-features/2.0/disclose"

PROTOCOL_PACKAGE = "acapy_agent.protocols_v2.discovery.v1_0"


class discover_features:
    async def __call__(self, *args, **kwargs):
        await self.handle(*args, **kwargs)

    @staticmethod
    async def handle(context, responder, payload):
        logger = logging.getLogger(__name__)
        their_did = context.message_receipt.sender_verkey.split("#")[0]
        our_did = context.message_receipt.recipient_verkey.split("#")[0]
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
    QUERIES: f"{PROTOCOL_PACKAGE}.message_types.discover_features",
}.items()

MESSAGE_TYPES = {
    QUERIES: f"{PROTOCOL_PACKAGE}.message_types.discover_features",
}
