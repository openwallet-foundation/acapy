"""Represents a connection request message under RFC 23 (DID exchange)."""

from marshmallow import EXCLUDE, fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from .....messaging.decorators.attach_decorator import (
    AttachDecorator,
    AttachDecoratorSchema,
)

from ..message_types import CONN23_REQUEST, PROTOCOL_PACKAGE

HANDLER_CLASS = f"{PROTOCOL_PACKAGE}.handlers.request_handler.Conn23RequestHandler"


class Conn23Request(AgentMessage):
    """Class representing a connection request under RFC 23 (DID exchange)."""

    class Meta:
        """Metadata for connection request under RFC 23 (DID exchange)."""

        handler_class = HANDLER_CLASS
        message_type = CONN23_REQUEST
        schema_class = "Conn23RequestSchema"

    def __init__(
        self,
        *,
        label: str = None,
        did: str = None,
        did_doc_attach: AttachDecorator = None,
        **kwargs,
    ):
        """
        Initialize connection request object under RFC 23 (DID exchange).

        Args:
            label: Label for this connection request
            image_url: Optional image URL for this connection request
            did_doc_attach: signed DID doc attachment
        """
        super().__init__(**kwargs)
        self.label = label
        self.did = did
        self.did_doc_attach = did_doc_attach


class Conn23RequestSchema(AgentMessageSchema):
    """Schema class for connection request under RFC 23 (DID exchange)."""

    class Meta:
        """DID exchange connection request schema class metadata."""

        model_class = Conn23Request
        signed_fields = ["did_doc_attach"]
        unknown = EXCLUDE

    label = fields.Str(
        required=True,
        description="Label for connection request",
        example="Request to connect with Bob",
    )
    did = fields.Str(description="DID of exchange", **INDY_DID)
    did_doc_attach = fields.Nested(
        AttachDecoratorSchema,
        required=False,
        description="As signed attachment, DID Doc associated with DID",
        data_key="did_doc~attach",
    )
