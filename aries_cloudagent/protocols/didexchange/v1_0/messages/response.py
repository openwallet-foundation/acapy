"""Represents a DID exchange response message under RFC 23."""

from typing import Optional
from marshmallow import EXCLUDE, fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from .....messaging.decorators.attach_decorator import (
    AttachDecorator,
    AttachDecoratorSchema,
)
from .....messaging.valid import GENERIC_DID_EXAMPLE, GENERIC_DID_VALIDATE
from ..message_types import DIDX_RESPONSE, PROTOCOL_PACKAGE

HANDLER_CLASS = f"{PROTOCOL_PACKAGE}.handlers.response_handler.DIDXResponseHandler"


class DIDXResponse(AgentMessage):
    """Class representing a DID exchange response under RFC 23."""

    class Meta:
        """Metadata for DID exchange response under RFC 23."""

        handler_class = HANDLER_CLASS
        message_type = DIDX_RESPONSE
        schema_class = "DIDXResponseSchema"

    def __init__(
        self,
        *,
        did: str = None,
        did_doc_attach: Optional[AttachDecorator] = None,
        **kwargs,
    ):
        """
        Initialize DID exchange response object under RFC 23.

        Args:
            image_url: Optional image URL for this response
            did_doc_attach: signed DID doc attachment
        """
        super().__init__(**kwargs)
        self.did = did
        self.did_doc_attach = did_doc_attach


class DIDXResponseSchema(AgentMessageSchema):
    """Schema class for DID exchange response under RFC 23."""

    class Meta:
        """DID exchange response schema class metadata."""

        model_class = DIDXResponse
        unknown = EXCLUDE

    did = fields.Str(
        validate=GENERIC_DID_VALIDATE,
        metadata={"description": "DID of exchange", "example": GENERIC_DID_EXAMPLE},
    )
    did_doc_attach = fields.Nested(
        AttachDecoratorSchema,
        required=False,
        data_key="did_doc~attach",
        metadata={"description": "As signed attachment, DID Doc associated with DID"},
    )
