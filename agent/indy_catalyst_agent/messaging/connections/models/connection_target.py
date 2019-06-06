"""Record used to handle routing of messages to another agent."""

from typing import Sequence

from marshmallow import fields

from ...models.base import BaseModel, BaseModelSchema


class ConnectionTarget(BaseModel):
    """Record used to handle routing of messages to another agent."""

    class Meta:
        """ConnectionTarget metadata."""

        schema_class = "ConnectionTargetSchema"

    def __init__(
        self,
        *,
        did: str = None,
        endpoint: str = None,
        label: str = None,
        recipient_keys: Sequence[str] = None,
        routing_keys: Sequence[str] = None,
        sender_key: str = None,
    ):
        """
        Initialize a ConnectionTarget instance.

        Args:
            did: A did for the connection
            endpoint: An endpoint for the connection
            label: A label for the connection
            recipient_key: A list of recipient keys
            routing_keys: A list of routing keys
        """
        self.did = did
        self.endpoint = endpoint
        self.label = label
        self.recipient_keys = list(recipient_keys) if recipient_keys else []
        self.routing_keys = list(routing_keys) if routing_keys else []
        self.sender_key = sender_key


class ConnectionTargetSchema(BaseModelSchema):
    """ConnectionTarget schema."""

    class Meta:
        """ConnectionTargetSchema metadata."""

        model_class = ConnectionTarget

    did = fields.Str(required=False)
    endpoint = fields.Str(required=False)
    label = fields.Str(required=False)
    recipient_keys = fields.List(fields.Str(), required=False)
    routing_keys = fields.List(fields.Str(), required=False)
    sender_key = fields.Str(required=False)
