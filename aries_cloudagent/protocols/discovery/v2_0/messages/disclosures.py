"""Represents a feature discovery disclosure message."""

from typing import Mapping, Sequence

from marshmallow import EXCLUDE, fields, Schema, ValidationError

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from .....messaging.models.base import BaseModelError

from ..message_types import DISCLOSURES, PROTOCOL_PACKAGE

HANDLER_CLASS = f"{PROTOCOL_PACKAGE}.handlers.disclosures_handler.DisclosuresHandler"


class ProtocolOrGoalCodeDescriptorField(fields.Field):
    """ProtocolDescriptor or GoalCodeDescriptor for Marshmallow."""

    def _serialize(self, value, attr, obj, **kwargs):
        return value

    def _deserialize(self, value, attr, data, **kwargs):
        try:
            GoalCodeDescriptorSchema().load(value)
            return value
        except ValidationError:
            try:
                ProtocolDescriptorSchema().load(value)
                return value
            except ValidationError:
                raise BaseModelError(
                    "Field should be ProtocolDescriptor or GoalCodeDescriptor"
                )


class ProtocolDescriptorSchema(Schema):
    """Schema for an entry in the protocols list."""

    id = fields.Str(required=True)
    feature_type = fields.Str(
        required=True, description="feature-type", data_key="feature-type"
    )
    roles = fields.List(
        fields.Str(
            description="Role: requester or responder",
            example="requester",
        ),
        required=False,
        allow_none=True,
        description="List of roles",
    )


class GoalCodeDescriptorSchema(Schema):
    """Schema for an entry in the goal_code list."""

    id = fields.Str(required=True)
    feature_type = fields.Str(
        required=True, description="feature-type", data_key="feature-type"
    )


class Disclosures(AgentMessage):
    """Represents a feature discovery disclosure, the response to a query message."""

    class Meta:
        """Disclose metadata."""

        handler_class = HANDLER_CLASS
        message_type = DISCLOSURES
        schema_class = "DisclosuresSchema"

    def __init__(self, *, disclosures: Sequence[Mapping] = None, **kwargs):
        """
        Initialize disclose message object.

        Args:
            disclosures: A mapping of protocol names to a dictionary of properties
        """
        super().__init__(**kwargs)
        self.disclosures = list(disclosures) if disclosures else []


class DisclosuresSchema(AgentMessageSchema):
    """Disclose message schema used in serialization/deserialization."""

    class Meta:
        """DiscloseSchema metadata."""

        model_class = Disclosures
        unknown = EXCLUDE

    disclosures = fields.List(
        ProtocolOrGoalCodeDescriptorField(),
        required=True,
        description="List of protocol or goal_code descriptors",
    )
