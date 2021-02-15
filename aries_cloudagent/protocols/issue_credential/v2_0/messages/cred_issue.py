"""Credential issue message."""

from typing import Sequence

from marshmallow import EXCLUDE, fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from .....messaging.decorators.attach_decorator import (
    AttachDecorator,
    AttachDecoratorSchema,
)
from .....messaging.valid import UUIDFour

from ..message_types import CRED_20_ISSUE, PROTOCOL_PACKAGE

from .cred_format import V20CredFormat, V20CredFormatSchema

HANDLER_CLASS = f"{PROTOCOL_PACKAGE}.handlers.cred_issue_handler.V20CredIssueHandler"


class V20CredIssue(AgentMessage):
    """Credential issue message."""

    class Meta:
        """V20CredIssue metadata."""

        handler_class = HANDLER_CLASS
        schema_class = "V20CredIssueSchema"
        message_type = CRED_20_ISSUE

    def __init__(
        self,
        _id: str = None,
        *,
        replacement_id: str = None,
        comment: str = None,
        formats: Sequence[V20CredFormat] = None,
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
        self.replacement_id = replacement_id
        self.comment = comment
        self.formats = list(formats) if formats else []
        self.credentials_attach = list(credentials_attach) if credentials_attach else []

    def cred(self, fmt: V20CredFormat.Format = None) -> dict:
        """
        Return attached credential.

        Args:
            fmt: format of attachment in list to decode and return

        """
        return (fmt or V20CredFormat.Format.INDY).get_attachment_data(
            self.formats,
            self.credentials_attach,
        )


class V20CredIssueSchema(AgentMessageSchema):
    """Credential issue schema."""

    class Meta:
        """Credential issue schema metadata."""

        model_class = V20CredIssue
        unknown = EXCLUDE

    replacement_id = fields.Str(
        description="Issuer-unique identifier to coordinate credential replacement",
        required=False,
        allow_none=False,
        example=UUIDFour.EXAMPLE,
    )
    comment = fields.Str(
        description="Human-readable comment", required=False, allow_none=True
    )
    formats = fields.Nested(
        V20CredFormatSchema,
        many=True,
        required=True,
        description="Acceptable credential formats",
    )
    credentials_attach = fields.Nested(
        AttachDecoratorSchema, many=True, required=True, data_key="credentials~attach"
    )
