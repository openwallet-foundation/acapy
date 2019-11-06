"""A credential offer content message."""

from marshmallow import fields

from ....messaging.agent_message import AgentMessage, AgentMessageSchema

from ..message_types import CREDENTIAL_OFFER, PROTOCOL_PACKAGE


HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers.credential_offer_handler.CredentialOfferHandler"
)


class CredentialOffer(AgentMessage):
    """Class representing a credential offer."""

    class Meta:
        """CredentialOffer metadata."""

        handler_class = HANDLER_CLASS
        schema_class = "CredentialOfferSchema"
        message_type = CREDENTIAL_OFFER

    def __init__(
        self,
        *,
        offer_json: str = None,
        credential_preview: dict = None,
        comment: str = None,
        **kwargs,
    ):
        """
        Initialize credential offer object.

        Args:
            offer_json: Credential offer json
        """
        super(CredentialOffer, self).__init__(**kwargs)
        self.offer_json = offer_json
        self.credential_preview = credential_preview
        self.comment = comment


class CredentialOfferSchema(AgentMessageSchema):
    """Credential offer schema."""

    class Meta:
        """Credential offer schema metadata."""

        model_class = CredentialOffer

    offer_json = fields.Str(required=True)
    credential_preview = fields.Dict(required=False)
    comment = fields.Str(required=False)
