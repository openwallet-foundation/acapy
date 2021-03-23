"""Represents a DID exchange request message under RFC 23."""

from marshmallow import EXCLUDE, fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from .....messaging.decorators.attach_decorator import (
    AttachDecorator,
    AttachDecoratorSchema,
)
from .....messaging.valid import INDY_DID

from ..message_types import DIDX_REQUEST, PROTOCOL_PACKAGE

HANDLER_CLASS = f"{PROTOCOL_PACKAGE}.handlers.request_handler.DIDXRequestHandler"


class DIDXRequest(AgentMessage):
    """Class representing a DID exchange request under RFC 23."""

    class Meta:
        """Metadata for DID exchange request under RFC 23."""

        handler_class = HANDLER_CLASS
        message_type = DIDX_REQUEST
        schema_class = "DIDXRequestSchema"

    def __init__(
        self,
        *,
        label: str = None,
        did: str = None,
        did_doc_attach: AttachDecorator = None,
        **kwargs,
    ):
        """
        Initialize DID exchange request object under RFC 23.

        Args:
            label: Label for this request
            did: DID for this request
            did_doc_attach: signed DID doc attachment
        """
        super().__init__(**kwargs)
        self.label = label
        self.did = did
        self.did_doc_attach = did_doc_attach


class DIDXRequestSchema(AgentMessageSchema):
    """Schema class for DID exchange request under RFC 23."""

    class Meta:
        """DID exchange request schema class metadata."""

        model_class = DIDXRequest
        unknown = EXCLUDE

    label = fields.Str(
        required=True,
        description="Label for DID exchange request",
        example="Request to connect with Bob",
    )
    did = fields.Str(description="DID of exchange", **INDY_DID)
    did_doc_attach = fields.Nested(
        AttachDecoratorSchema,
        required=False,
        description="As signed attachment, DID Doc associated with DID",
        data_key="did_doc~attach",
    )
