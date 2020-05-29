"""A credential content message."""

from typing import Sequence, Text

from marshmallow import fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from .....messaging.decorators.attach_decorator import (
    AttachDecorator,
    AttachDecoratorSchema,
)

from .service import Service, ServiceSchema

from ..message_types import PROTOCOL_PACKAGE, INVITATION

HANDLER_CLASS = f"{PROTOCOL_PACKAGE}.handlers.invitation_handler.InvitationHandler"


class Invitation(AgentMessage):
    """Class representing an out of band invitation message."""

    class Meta:
        """Credential metadata."""

        handler_class = HANDLER_CLASS
        schema_class = "InvitationSchema"
        message_type = INVITATION

    def __init__(
        self,
        _id: str = None,
        *,
        comment: str = None,
        label: str = None,
        handshake_protocols: Sequence[Text] = None,
        request_attach: Sequence[AttachDecorator] = None,
        service: Sequence[Service] = None,
        **kwargs,
    ):
        """
        Initialize invitation object.

        Args:
            request_attach: request attachments

        """
        super().__init__(_id=_id, **kwargs)
        self.label = label
        self.handshake_protocols = (
            list(handshake_protocols) if handshake_protocols else []
        )
        self.request_attach = list(request_attach) if request_attach else []
        self.service = list(service) if service else []

    @classmethod
    def wrap_message(cls, message: dict) -> AttachDecorator:
        """Convert an aries message to an attachment decorator."""
        return AttachDecorator.from_aries_msg(
            message=message, ident="request-0"
        )


class InvitationSchema(AgentMessageSchema):
    """Invitation schema."""

    class Meta:
        """Invitation schema metadata."""

        model_class = Invitation

    label = fields.Str(required=False, description="Optional label", example="Bob")
    handshake_protocols = fields.List(fields.String, required=False, many=True)
    request_attach = fields.Nested(
        AttachDecoratorSchema, required=True, many=True, data_key="request~attach"
    )
    service = fields.Nested(ServiceSchema, required=False, many=True)
