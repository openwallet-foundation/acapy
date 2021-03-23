"""Record used to handle routing of messages to another agent."""

from typing import Sequence

from marshmallow import EXCLUDE, fields

from ...messaging.models.base import BaseModel, BaseModelSchema
from ...messaging.valid import INDY_DID, INDY_RAW_PUBLIC_KEY


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
        unknown = EXCLUDE

    did = fields.Str(required=False, description="", **INDY_DID)
    endpoint = fields.Str(
        required=False,
        description="Connection endpoint",
        example="http://192.168.56.102:8020",
    )
    label = fields.Str(required=False, description="Connection label", example="Bob")
    recipient_keys = fields.List(
        fields.Str(description="Recipient public key", **INDY_RAW_PUBLIC_KEY),
        required=False,
        description="List of recipient keys",
    )
    routing_keys = fields.List(
        fields.Str(description="Routing key", **INDY_RAW_PUBLIC_KEY),
        data_key="routingKeys",
        required=False,
        description="List of routing keys",
    )
    sender_key = fields.Str(
        required=False, description="Sender public key", **INDY_RAW_PUBLIC_KEY
    )
