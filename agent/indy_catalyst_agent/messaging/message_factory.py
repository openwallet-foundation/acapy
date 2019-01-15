from .message_types import MessageTypes

from .connections.connection_invitation import ConnectionInvitation
from .connections.connection_request import ConnectionRequest
from .connections.connection_response import ConnectionResponse

from .credentials.credential_offer import CredentialOffer
from .credentials.credential_request import CredentialRequest
from .credentials.credential import Credential

from .proofs.proof_request import ProofRequest
from .proofs.proof import Proof

from .routing.forward import Forward


class MessageParseError(Exception):
    pass


class MessageFactory:
    """
    Message factory for deserializing message json and obtaining relevant
    message class
    """

    @classmethod
    def make_message(cls, obj):
        """
        Given a dict describing a message, this method
        returns an instance of the related message class.
        """

        if not obj.get("@type"):
            raise MessageParseError("Message does not contain '@type' parameter")

        # Connection Messages
        if obj["@type"] == MessageTypes.CONNECTION_INVITATION.value:
            return ConnectionInvitation.deserialize(obj)
        elif obj["@type"] == MessageTypes.CONNECTION_REQUEST.value:
            return ConnectionRequest.deserialize(obj)
        elif obj["@type"] == MessageTypes.CONNECTION_RESPONSE.value:
            return ConnectionResponse.deserialize(obj)

        # Credential Messages
        elif obj["@type"] == MessageTypes.CREDENTIAL.value:
            return Credential.deserialize(obj)
        elif obj["@type"] == MessageTypes.CREDENTIAL_OFFER.value:
            return CredentialOffer.deserialize(obj)
        elif obj["@type"] == MessageTypes.CREDENTIAL_REQUEST.value:
            return CredentialRequest.deserialize(obj)

        # Proof Messages
        elif obj["@type"] == MessageTypes.PROOF_REQUEST.value:
            return ProofRequest.deserialize(obj)
        elif obj["@type"] == MessageTypes.PROOF.value:
            return Proof.deserialize(obj)

        # Routing Messages
        elif obj["@type"] == MessageTypes.FORWARD.value:
            return Forward.deserialize(obj)

        else:
            raise MessageParseError(f"Unrecognized message type {obj['@type']}")

