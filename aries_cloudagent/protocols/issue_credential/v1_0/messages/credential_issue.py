"""A credential content message."""

from typing import Sequence

from marshmallow import EXCLUDE, fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from .....messaging.decorators.attach_decorator import (
    AttachDecorator,
    AttachDecoratorSchema,
)
from ..message_types import ATTACH_DECO_IDS, CREDENTIAL_ISSUE, PROTOCOL_PACKAGE

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers.credential_issue_handler.CredentialIssueHandler"
)


class CredentialIssue(AgentMessage):
    """Class representing a credential."""

    class Meta:
        """Credential metadata."""

        handler_class = HANDLER_CLASS
        schema_class = "CredentialIssueSchema"
        message_type = CREDENTIAL_ISSUE

    def __init__(
        self,
        _id: str = None,
        *,
        comment: str = None,
        credentials_attach: Sequence[AttachDecorator] = None,
        **kwargs,
    ):
        """
        Initialize credential issue object.

        Args:
            comment: optional comment
            credentials_attach: credentials attachments

        """
        super().__init__(_id=_id, **kwargs)
        self.comment = comment
        self.credentials_attach = list(credentials_attach) if credentials_attach else []

    def indy_credential(self, index: int = 0):
        """
        Retrieve and decode indy credential from attachment.

        Args:
            index: ordinal in attachment list to decode and return
                (typically, list has length 1)

        """
        return self.credentials_attach[index].content

    @classmethod
    def wrap_indy_credential(cls, indy_cred: dict) -> AttachDecorator:
        """Convert an indy credential offer to an attachment decorator."""
        return AttachDecorator.data_base64(
            mapping=indy_cred, ident=ATTACH_DECO_IDS[CREDENTIAL_ISSUE]
        )


class CredentialIssueSchema(AgentMessageSchema):
    """Credential schema."""

    class Meta:
        """Credential schema metadata."""

        model_class = CredentialIssue
        unknown = EXCLUDE

    comment = fields.Str(
        required=False,
        allow_none=True,
        metadata={"description": "Human-readable comment"},
    )
    credentials_attach = fields.Nested(
        AttachDecoratorSchema, required=True, many=True, data_key="credentials~attach"
    )
