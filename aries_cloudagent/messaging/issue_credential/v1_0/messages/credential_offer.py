"""A credential offer content message."""


from typing import Sequence

from marshmallow import fields, pre_load, ValidationError

from ....agent_message import AgentMessage, AgentMessageSchema
from ....models.base import resolve_meta_property
from ..decorators.attach_decorator import AttachDecorator, AttachDecoratorSchema
from ..message_types import CREDENTIAL_OFFER
from .inner.credential_preview import CredentialPreview, CredentialPreviewSchema


HANDLER_CLASS = (
    "aries_cloudagent.messaging.issue_credential.v1_0.handlers."
    + "credential_offer_handler.CredentialOfferHandler"
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
        _id: str = None,
        *,
        comment: str = None,
        credential_preview: CredentialPreview = None,
        offers_attach: Sequence[AttachDecorator] = None,
        **kwargs
    ):
        """
        Initialize credential offer object.

        Args:
            comment: optional human-readable comment
            credential_preview: credential preview
            offers_attach: list of offer attachments

        """
        super().__init__(
            _id=_id,
            **kwargs
        )
        self.comment = comment
        self.credential_preview = (
            credential_preview if credential_preview else CredentialPreview()
        )
        self.offers_attach = list(offers_attach) if offers_attach else []

    def indy_offer(self, index: int = 0):
        """
        Retrieve and decode indy offer from attachment.

        Args:
            index: ordinal in attachment list to decode and return
                (typically, list has length 1)

        """
        return self.offers_attach[index].indy_dict


class CredentialOfferSchema(AgentMessageSchema):
    """Credential offer schema."""

    class Meta:
        """Credential offer schema metadata."""

        model_class = CredentialOffer

    comment = fields.Str(required=False, allow_none=False)
    credential_preview = fields.Nested(CredentialPreviewSchema, required=False)
    offers_attach = fields.Nested(
        AttachDecoratorSchema,
        required=True,
        many=True,
        data_key='offers~attach'
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
            skip_attrs=["offers_attach"]
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
