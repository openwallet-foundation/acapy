"""A credential content message."""


from typing import Sequence

from marshmallow import fields, pre_load, ValidationError

from ....agent_message import AgentMessage, AgentMessageSchema
from ....models.base import resolve_meta_property
from ..decorators.attach_decorator import AttachDecorator, AttachDecoratorSchema
from ..message_types import CREDENTIAL_ISSUE


HANDLER_CLASS = (
    "aries_cloudagent.messaging.issue_credential.v1_0.handlers."
    + "credential_issue_handler.CredentialIssueHandler"
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
        **kwargs
    ):
        """
        Initialize credential issue object.

        Args:
            comment: optional comment
            credentials_attach: credentials attachments

        """
        super().__init__(
            _id=_id,
            **kwargs
        )
        self.comment = comment
        self.credentials_attach = list(credentials_attach) if credentials_attach else []

    def indy_credential(self, index: int = 0):
        """
        Retrieve and decode indy credential from attachment.

        Args:
            index: ordinal in attachment list to decode and return
                (typically, list has length 1)

        """
        return self.credentials_attach[index].indy_dict


class CredentialIssueSchema(AgentMessageSchema):
    """Credential schema."""

    class Meta:
        """Credential schema metadata."""

        model_class = CredentialIssue

    comment = fields.Str(required=False)
    credentials_attach = fields.Nested(
        AttachDecoratorSchema,
        required=True,
        many=True,
        data_key='credentials~attach'
    )

    @pre_load
    def extract_decorators(self, data):
        """
        Pre-load hook to extract the decorators and check the signed fields.

        Args:
            data: Incoming data to parse

        Returns:
            Parsed and modified data

        Raises:
            ValidationError: If a field signature does not correlate
            to a field in the message
            ValidationError: If the message defines both a field signature
            and a value for the same field
            ValidationError: If there is a missing field signature

        """
        processed = self._decorators.extract_decorators(
            data,
            self.__class__,
            skip_attrs=["credentials_attach"]
        )

        expect_fields = resolve_meta_property(self, "signed_fields") or ()
        found_signatures = {}
        for field_name, field in self._decorators.fields.items():
            if "sig" in field:
                if field_name not in expect_fields:
                    raise ValidationError(
                        f"Encountered unexpected field signature: {field_name}"
                    )
                if field_name in processed:
                    raise ValidationError(
                        f"Message defines both field signature and value: {field_name}"
                    )
                found_signatures[field_name] = field["sig"]
                processed[field_name], _ts = field["sig"].decode()
        for field_name in expect_fields:
            if field_name not in found_signatures:
                raise ValidationError(f"Expected field signature: {field_name}")
        return processed
