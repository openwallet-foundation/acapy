"""Credential offer message."""

from typing import Sequence

from marshmallow import EXCLUDE, fields, validates_schema, ValidationError

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from .....messaging.decorators.attach_decorator import (
    AttachDecorator,
    AttachDecoratorSchema,
)
from .....messaging.valid import UUIDFour

from ..message_types import CRED_20_OFFER, PROTOCOL_PACKAGE

from .cred_format import V20CredFormat, V20CredFormatSchema
from .inner.cred_preview import V20CredPreview, V20CredPreviewSchema

HANDLER_CLASS = f"{PROTOCOL_PACKAGE}.handlers.cred_offer_handler.V20CredOfferHandler"


class V20CredOffer(AgentMessage):
    """Credential offer."""

    class Meta:
        """V20CredOffer metadata."""

        handler_class = HANDLER_CLASS
        schema_class = "V20CredOfferSchema"
        message_type = CRED_20_OFFER

    def __init__(
        self,
        _id: str = None,
        *,
        replacement_id: str = None,
        comment: str = None,
        credential_preview: V20CredPreview = None,
        formats: Sequence[V20CredFormat] = None,
        offers_attach: Sequence[AttachDecorator] = None,
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
        self.replacement_id = replacement_id
        self.comment = comment
        self.credential_preview = credential_preview
        self.formats = list(formats) if formats else []
        self.offers_attach = list(offers_attach) if offers_attach else []

    def attachment(self, fmt: V20CredFormat.Format = None) -> dict:
        """
        Return attached offer.

        Args:
            fmt: format of attachment in list to decode and return

        """
        target_format = (
            fmt
            if fmt
            else next(
                filter(
                    lambda ff: ff,
                    [V20CredFormat.Format.get(f.format) for f in self.formats],
                ),
                None,
            )
        )
        return (
            target_format.get_attachment_data(self.formats, self.offers_attach)
            if target_format
            else None
        )


class V20CredOfferSchema(AgentMessageSchema):
    """Credential offer schema."""

    class Meta:
        """Credential offer schema metadata."""

        model_class = V20CredOffer
        unknown = EXCLUDE

    replacement_id = fields.Str(
        description="Issuer-unique identifier to coordinate credential replacement",
        required=False,
        allow_none=False,
        example=UUIDFour.EXAMPLE,
    )
    comment = fields.Str(
        description="Human-readable comment",
        required=False,
        allow_none=True,
    )
    credential_preview = fields.Nested(V20CredPreviewSchema, required=False)
    formats = fields.Nested(
        V20CredFormatSchema,
        many=True,
        required=True,
        description="Acceptable credential formats",
    )
    offers_attach = fields.Nested(
        AttachDecoratorSchema,
        required=True,
        many=True,
        data_key="offers~attach",
        description="Offer attachments",
    )

    @validates_schema
    def validate_fields(self, data, **kwargs):
        """Validate attachments per format."""

        def get_attach_by_id(attach_id):
            """Return attachment with input identifier."""
            for atch in attachments:
                if atch.ident == attach_id:
                    return atch
            raise ValidationError(f"No attachment for attach_id {attach_id} in formats")

        formats = data.get("formats") or []
        attachments = data.get("offers_attach") or []
        if len(formats) != len(attachments):
            raise ValidationError("Formats/attachments length mismatch")

        for fmt in formats:
            atch = get_attach_by_id(fmt.attach_id)
            cred_format = V20CredFormat.Format.get(fmt.format)

            if cred_format:
                cred_format.validate_fields(CRED_20_OFFER, atch.content)
