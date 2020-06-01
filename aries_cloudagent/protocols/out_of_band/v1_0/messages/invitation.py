"""A credential content message."""

from typing import Sequence, Text, Union

from marshmallow import fields, validates_schema, ValidationError

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from .....messaging.decorators.attach_decorator import (
    AttachDecorator,
    AttachDecoratorSchema,
)

from .service import Service, ServiceSchema

from ..message_types import PROTOCOL_PACKAGE, INVITATION

HANDLER_CLASS = f"{PROTOCOL_PACKAGE}.handlers.invitation_handler.InvitationHandler"


class ServiceFieldSerializationError(Exception):
    pass


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
        service: Sequence[Union[Service, Text]] = None,
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
        return AttachDecorator.from_aries_msg(message=message, ident="request-0")


class ServiceField(fields.Nested):
    def _serialize(self, value, attr, obj, **kwargs):
        if not value:
            return []

        serialized_elements = []
        for el in value:
            if type(el) is str:
                serialized_elements.append(el)
            elif type(el) is Service:
                serialized_elements.append(el.serialize())
            else:
                raise ServiceFieldSerializationError(
                    f"Incompatible service element type: {type(el)} "
                )
        return serialized_elements


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
    # service = ServiceField(ServiceSchema, required=False, many=True)

    @validates_schema
    def validate_fields(self, data, **kwargs):
        """
        Validate schema fields.
        Args:
            data: The data to validate
        Raises:
            ValidationError: If any of the fields do not validate
        """
        handshake_protocols = data.get("handshake_protocols")
        request_attach = data.get("request_attach")
        if not (
            (handshake_protocols and len(handshake_protocols) > 0)
            and (request_attach and len(request_attach) > 0)
        ):
            raise ValidationError(
                "Model must include handshake_protocols or request_attach or both"
            )
