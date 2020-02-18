"""A credential presentation message."""

from marshmallow import fields

from ....messaging.agent_message import AgentMessage, AgentMessageSchema

from ..message_types import CREDENTIAL_PRESENTATION, PROTOCOL_PACKAGE


HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers."
    "credential_presentation_handler.CredentialPresentationHandler"
)


class CredentialPresentation(AgentMessage):
    """Class representing a credential presentation."""

    class Meta:
        """CredentialPresentation metadata."""

        handler_class = HANDLER_CLASS
        schema_class = "CredentialPresentationSchema"
        message_type = CREDENTIAL_PRESENTATION

    def __init__(self, presentation: str = None, comment: str = None, **kwargs):
        """
        Initialize credential presentation object.

        Args:
            presentation: Credential presentation json string
            comment: Comment
        """
        super(CredentialPresentation, self).__init__(**kwargs)
        self.presentation = presentation
        self.comment = comment


class CredentialPresentationSchema(AgentMessageSchema):
    """CredentialPresentation schema."""

    class Meta:
        """CredentialPresentationSchema metadata."""

        model_class = CredentialPresentation

    presentation = fields.Str(required=True)
    comment = fields.Str(required=False)
