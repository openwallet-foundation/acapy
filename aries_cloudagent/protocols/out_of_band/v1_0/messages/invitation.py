"""A credential content message."""

from typing import Sequence, Text, Union

from marshmallow import fields, validates_schema, ValidationError, pre_load, post_dump

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
        """Invitation metadata."""

        handler_class = HANDLER_CLASS
        schema_class = "InvitationSchema"
        message_type = INVITATION

    def __init__(
        self,
        # _id: str = None,
        *,
        comment: str = None,
        label: str = None,
        handshake_protocols: Sequence[Text] = None,
        request_attach: Sequence[AttachDecorator] = None,
        # When loading, we sort service in the two lists
        service: Sequence[Union[Service, Text]] = None,
        service_blocks: Sequence[Service] = None,
        service_dids: Sequence[Text] = None,
        **kwargs,
    ):
        """
        Initialize invitation object.

        Args:
            request_attach: request attachments

        """
        # super().__init__(_id=_id, **kwargs)
        super().__init__(**kwargs)
        self.label = label
        self.handshake_protocols = (
            list(handshake_protocols) if handshake_protocols else []
        )
        self.request_attach = list(request_attach) if request_attach else []

        # In order to accept and validate both string entries and
        # dict block entries, we include both in schema and manipulate
        # data in pre_load and post_dump
        self.service_blocks = list(service_blocks) if service_blocks else []
        self.service_dids = list(service_dids) if service_dids else []

        # In the case of loading, we need to sort
        # the entries into relevant lists for schema validation
        for s in service or []:
            if type(s) is Service:
                self.service_blocks.append(s)
            elif type(s) is str:
                self.service_dids.append(s)

    @classmethod
    def wrap_message(cls, message: dict) -> AttachDecorator:
        """Convert an aries message to an attachment decorator."""
        return AttachDecorator.from_aries_msg(message=message, ident="request-0")


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

    service_blocks = fields.Nested(ServiceSchema, many=True)
    service_dids = fields.List(fields.String, many=True)

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
            or (request_attach and len(request_attach) > 0)
        ):
            raise ValidationError(
                "Model must include non-empty "
                + "handshake_protocols or request_attach or both"
            )

        # service = data.get("service")
        # if not ((service and len(service) > 0)):
        #     raise ValidationError(
        #         "Model must include non-empty service array"
        #     )

    @pre_load
    def pre_load(self, data, **kwargs):
        """Pre load hook."""
        data["service_dids"] = []
        data["service_blocks"] = []

        for service_entry in data["service"]:
            if type(service_entry) is str:
                data["service_dids"].append(service_entry)
            if type(service_entry) is dict:
                data["service_blocks"].append(service_entry)

        del data["service"]

        return data

    @post_dump
    def post_dump(self, data, **kwargs):
        """Post dump hook."""
        data["service"] = []

        for service_entry in data["service_dids"]:
            data["service"].append(service_entry)
        for service_entry in data["service_blocks"]:
            data["service"].append(service_entry)

        del data["service_dids"]
        del data["service_blocks"]

        return data
