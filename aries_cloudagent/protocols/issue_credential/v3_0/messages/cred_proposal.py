"""Credential proposal message."""

from typing import Sequence

from marshmallow import EXCLUDE, fields, validates_schema, ValidationError

from .....messaging.agent_message import AgentMessage, AgentMessageSchemaV2
from .....messaging.decorators.attach_decorator_didcomm_v2_cred import (
    AttachDecorator,
    AttachDecoratorSchema,
)
from ..message_types import (
    CRED_30_PROPOSAL,
    PROTOCOL_PACKAGE,
)
from .cred_body import V30CredBodySchema, V30CredBody
from .cred_format import V30CredFormat

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers.cred_proposal_handler.V30CredProposalHandler"
)


class V30CredProposal(AgentMessage):
    """Credential proposal."""

    class Meta:
        """V30CredProposal metadata."""

        handler_class = HANDLER_CLASS
        schema_class = "V30CredProposalSchema"
        message_type = CRED_30_PROPOSAL

    def __init__(
        self,
        _id: str = None,
        _body: V30CredBody = None,
        attachments: Sequence[AttachDecorator] = None,
        **kwargs,
    ):
        """
        Initialize credential proposal object.

        Args:
            comment: optional human-readable comment
            credential_proposal: proposed credential preview
            formats: acceptable attachment formats
            filters_attach: list of attachments filtering credential proposal

        """
        super().__init__(_id=_id, **kwargs)
        self._body = _body
        self.attachments = list(attachments) if attachments else []

    def attachment(self, fmt: V30CredFormat.Format = None) -> dict:
        """Return attachment if exists else returns none."""

        if len(self.attachments) != 0:
            for att in self.attachments:
                try:
                    if V30CredFormat.Format.get(att.format.format).api == fmt.api:
                        return att.content
                except AttributeError:
                    return None
        else:
            return None


class V30CredProposalSchema(AgentMessageSchemaV2):
    """Credential proposal schema."""

    class Meta:
        """Credential proposal schema metadata."""

        model_class = V30CredProposal
        unknown = EXCLUDE

    _body = fields.Nested(
        V30CredBodySchema,
        required=True,
        allow_none=False,
        many=False,
        data_key="body",
    )
    attachments = fields.Nested(
        AttachDecoratorSchema,
        required=False,
        many=True,
        data_key="attachments",
        description="Attachment per acceptable format on corresponding identifier",
    )

    @validates_schema
    def validate_fields(self, data, **kwargs):
        """Validate presentation attachment per format."""
        print(f"data {data}")
        attachments = data.get("attachments") or []
        print(f"attach{attachments}")
        formats = []
        for atch in attachments:
            formats.append(atch.format)
        print(f"formats {formats}")

        if len(formats) != len(attachments):
            raise ValidationError("Formats/attachments length mismatch")

        for atch in attachments:
            pres_format = V30CredFormat.Format.get(atch.format.format)
            if pres_format:
                pres_format.validate_fields(CRED_30_PROPOSAL, atch.content)
