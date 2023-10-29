"""Represents a DID exchange request message under RFC 23."""

from typing import Optional

from marshmallow import EXCLUDE, fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from .....messaging.decorators.attach_decorator import (
    AttachDecorator,
    AttachDecoratorSchema,
)
from .....messaging.valid import GENERIC_DID_EXAMPLE, GENERIC_DID_VALIDATE
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
        label: Optional[str] = None,
        did: Optional[str] = None,
        did_doc_attach: Optional[AttachDecorator] = None,
        goal_code: Optional[str] = None,
        goal: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize DID exchange request object under RFC 23.

        Args:
            label: Label for this request
            did: DID for this request
            did_doc_attach: signed DID doc attachment
            goal_code: (optional) is a self-attested code the receiver may want to
              display to the user or use in automatically deciding what to do with
              the request message. The goal code might be used particularly when the
              request is sent to a resolvable DID without reference to a specfic
              invitation.
            goal: (optional) is a self-attested string that the receiver may want to
              display to the user about the context-specific goal of the request message.
        """
        super().__init__(**kwargs)
        self.label = label
        self.did = did
        self.did_doc_attach = did_doc_attach
        self.goal_code = goal_code
        self.goal = goal


class DIDXRequestSchema(AgentMessageSchema):
    """Schema class for DID exchange request under RFC 23."""

    class Meta:
        """DID exchange request schema class metadata."""

        model_class = DIDXRequest
        unknown = EXCLUDE

    label = fields.Str(
        required=True,
        metadata={
            "description": "Label for DID exchange request",
            "example": "Request to connect with Bob",
        },
    )
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
    goal_code = fields.Str(
        required=False,
        metadata={
            "description": (
                "A self-attested code the receiver may want to display to the user or"
                " use in automatically deciding what to do with the out-of-band message"
            ),
            "example": "issue-vc",
        },
    )
    goal = fields.Str(
        required=False,
        metadata={
            "description": (
                "A self-attested string that the receiver may want to display to the"
                " user about the context-specific goal of the out-of-band message"
            ),
            "example": "To issue a Faber College Graduate credential",
        },
    )
