"""Sane defaults for known message definitions."""

from .messaging.message_factory import MessageFactory
from .messaging.message_types import MessageTypes

from .messaging.basicmessage.message_types import MESSAGE_TYPES as BASICMESSAGE_MESSAGES
from .messaging.connections.message_types import MESSAGE_TYPES as CONNECTION_MESSAGES
from .messaging.discovery.message_types import MESSAGE_TYPES as DISCOVERY_MESSAGES
from .messaging.trustping.message_types import MESSAGE_TYPES as TRUSTPING_MESSAGES
from .messaging.routing.message_types import MESSAGE_TYPES as ROUTING_MESSAGES

# TODO move message registration to the module level

CREDENTIAL_MESSAGES = {
    MessageTypes.CREDENTIAL.value: (
        "indy_catalyst_agent.messaging.credentials.messages.credential.Credential"
    ),
    MessageTypes.CREDENTIAL_OFFER.value: (
        "indy_catalyst_agent.messaging.credentials.messages.credential_offer"
        + ".CredentialOffer"
    ),
    MessageTypes.CREDENTIAL_REQUEST.value: (
        "indy_catalyst_agent.messaging.credentials.messages.credential_request"
        + ".CredentialRequest"
    ),
}

PROOF_MESSAGES = {
    MessageTypes.PROOF_REQUEST.value: (
        "indy_catalyst_agent.messaging.proofs.messages.proof_request.ProofRequest",
    ),
    MessageTypes.PROOF.value: (
        "indy_catalyst_agent.messaging.proofs.messages.proof.Proof"
    ),
}


def default_message_factory() -> MessageFactory:
    """Message factory for default message types."""
    factory = MessageFactory()

    factory.register_message_types(
        BASICMESSAGE_MESSAGES,
        CONNECTION_MESSAGES,
        # CREDENTIAL_MESSAGES,
        # PROOF_MESSAGES,
        DISCOVERY_MESSAGES,
        ROUTING_MESSAGES,
        TRUSTPING_MESSAGES,
    )

    return factory
