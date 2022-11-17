"""Credential offer message."""

from typing import Sequence

from marshmallow import EXCLUDE, fields, validates_schema, ValidationError


from aries_cloudagent.protocols.issue_credential.v3_0.messages.cred_format import (
    V30CredFormat,
)

from .....messaging.agent_message import AgentMessage, AgentMessageSchemaV2
from .....messaging.decorators.attach_decorator_didcomm_v2_cred import (
    AttachDecorator,
    AttachDecoratorSchema,
)
from ..message_types import CRED_30_OFFER, PROTOCOL_PACKAGE
from .cred_body import V30CredBody, V30CredBodySchema

# from .cred_format import V30CredFormat, V30CredFormatSchema

HANDLER_CLASS = f"{PROTOCOL_PACKAGE}.handlers.cred_offer_handler.V30CredOfferHandler"


class V30CredOffer(AgentMessage):
    """Credential offer."""

    class Meta:
        """V30CredOffer metadata."""

        handler_class = HANDLER_CLASS
        schema_class = "V30CredOfferSchema"
        message_type = CRED_30_OFFER

    def __init__(
        self,
        _id: str = None,
        _body: V30CredBody = None,
        attachments: Sequence[AttachDecorator] = None,
        **kwargs,
    ):
        """
        Initialize credential offer object.

        Args:
            replacement_id: unique to issuer, to coordinate credential replacement
            comment: optional human-readable comment
            credential_preview: credential preview
            formats: acceptable attachment formats
            offers_attach: list of offer attachments

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


class V30CredOfferSchema(AgentMessageSchemaV2):
    """Credential offer schema."""

    class Meta:
        """Credential offer schema metadata."""

        model_class = V30CredOffer
        unknown = EXCLUDE

    _body = fields.Nested(
        V30CredBodySchema, required=True, allow_none=False, data_key="body", many=False
    )
    attachments = fields.Nested(
        AttachDecoratorSchema,
        required=True,
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
            # atch = get_attach_by_id(fmt.attach_id)
            pres_format = V30CredFormat.Format.get(atch.format.format)
            if pres_format:
                pres_format.validate_fields(CRED_30_OFFER, atch.content)
