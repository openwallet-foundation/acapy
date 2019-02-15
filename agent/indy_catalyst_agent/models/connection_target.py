"""
Record used to handle routing of messages to another agent
"""

from typing import Sequence

from marshmallow import fields

from .base import BaseModel, BaseModelSchema


class ConnectionTarget(BaseModel):
    class Meta:
        schema_class = "ConnectionTargetSchema"

    def __init__(
        self,
        *,
        endpoint: str = None,
        recipient_keys: Sequence[str] = None,
        routing_keys: Sequence[str] = None,
        sender_key: str = None,
    ):
        self.endpoint = endpoint
        self.recipient_keys = list(recipient_keys) if recipient_keys else []
        self.routing_keys = list(routing_keys) if routing_keys else []
        self.sender_key = sender_key


class ConnectionTargetSchema(BaseModelSchema):
    class Meta:
        model_class = ConnectionTarget

    endpoint = fields.Str(required=False)
    recipient_keys = fields.List(fields.Str(), required=False)
    routing_keys = fields.List(fields.Str(), required=False)
    sender_key = fields.Str(required=False)
