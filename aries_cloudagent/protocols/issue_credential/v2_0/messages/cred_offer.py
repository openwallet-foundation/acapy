"""Credential offer message."""

from typing import Sequence

from marshmallow import EXCLUDE, fields

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
            offers_attach: list of offer attachments

        """
        super().__init__(_id=_id, **kwargs)
        self.replacement_id = replacement_id
        self.comment = comment
        self.credential_preview = credential_preview
        self.formats = list(formats) if formats else []
        self.offers_attach = list(offers_attach) if offers_attach else []

    def offer(self, fmt: V20CredFormat.Format = None) -> dict:
        """
        Return attached offer.

        Args:
            fmt: format of attachment in list to decode and return

        """
        return (fmt or V20CredFormat.Format.INDY).get_attachment_data(
            self.formats,
            self.offers_attach,
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
        AttachDecoratorSchema, required=True, many=True, data_key="offers~attach"
    )
