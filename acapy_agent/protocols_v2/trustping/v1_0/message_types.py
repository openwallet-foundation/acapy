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
DEBUG = "https://didcomm.org/basicmessage/2.0/message"

PROTOCOL_PACKAGE = "acapy_agent.protocols_v2.trustping.v1_0"

class test_func:
    async def __call__(self, *args, **kwargs):
        await self.handle(*args, **kwargs)
    @staticmethod
    async def handle(context, responder, payload):
        message = payload
        session = await context.profile.session()
        ctx = session
        messaging = ctx.inject(DIDCommMessaging)
        routing_service = ctx.inject(RoutingService)
        frm = message.get("from")
        #destination = await routing_service._resolve_services(messaging.resolver, frm)
        services = await routing_service._resolve_services(messaging.resolver, frm)
        chain = [
            {
                "did": frm,
                "service": services,
            }
        ]

        # Loop through service DIDs until we run out of DIDs to forward to
        to_did = services[0].service_endpoint.uri
        found_forwardable_service = await routing_service.is_forwardable_service(
            messaging.resolver, services[0]
        )
        while found_forwardable_service:
            services = await routing_service._resolve_services(messaging.resolver, to_did)
            if services:
                chain.append(
                    {
                        "did": to_did,
                        "service": services,
                    }
                )
                to_did = services[0].service_endpoint.uri
            found_forwardable_service = (
                await routing_service.is_forwardable_service(messaging.resolver, services[0])
                if services
                else False
            )
        destination = [
            ConnectionTarget(
                did=context.message_receipt.sender_verkey,
                endpoint=service.service_endpoint.uri,
                recipient_keys=[context.message_receipt.sender_verkey],
                sender_key=context.message_receipt.recipient_verkey,
            )
            for service in chain[-1]["service"]
        ]
        logger = logging.getLogger(__name__)
        error_result = V2AgentMessage(
            message={
                "type": "https://didcomm.org/basicmessage/2.0/message",
                "body": {
                    "content": "Hello from acapy",
                },
                "to": [context.message_receipt.sender_verkey.split('#')[0]],
                "from": context.message_receipt.recipient_verkey.split('#')[0],
                "lang": "en",
            }
        )
        await responder.send_reply(error_result, target_list=destination)

HANDLERS = {
    DEBUG: f"{PROTOCOL_PACKAGE}.message_types.test_func",
}.items()

MESSAGE_TYPES = {
        DEBUG: f"{PROTOCOL_PACKAGE}.message_types.test_func",
}
