"""Record used to handle routing of messages to another agent."""

from typing import Optional, Sequence

from marshmallow import EXCLUDE, fields

from ...messaging.models.base import BaseModel, BaseModelSchema
from ...messaging.valid import (
    GENERIC_DID_EXAMPLE,
    GENERIC_DID_VALIDATE,
    INDY_RAW_PUBLIC_KEY_EXAMPLE,
    INDY_RAW_PUBLIC_KEY_VALIDATE,
)


class ConnectionTarget(BaseModel):
    """Record used to handle routing of messages to another agent."""

    class Meta:
        """ConnectionTarget metadata."""

        schema_class = "ConnectionTargetSchema"

    def __init__(
        self,
        *,
        did: Optional[str] = None,
        endpoint: Optional[str] = None,
        label: Optional[str] = None,
        recipient_keys: Optional[Sequence[str]] = None,
        routing_keys: Optional[Sequence[str]] = None,
        sender_key: Optional[str] = None,
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

    did = fields.Str(
        required=False,
        validate=GENERIC_DID_VALIDATE,
        metadata={"description": "", "example": GENERIC_DID_EXAMPLE},
    )
    endpoint = fields.Str(
        required=False,
        metadata={
            "description": "Connection endpoint",
            "example": "http://192.168.56.102:8020",
        },
    )
    label = fields.Str(
        required=False, metadata={"description": "Connection label", "example": "Bob"}
    )
    recipient_keys = fields.List(
        fields.Str(
            validate=INDY_RAW_PUBLIC_KEY_VALIDATE,
            metadata={
                "description": "Recipient public key",
                "example": INDY_RAW_PUBLIC_KEY_EXAMPLE,
            },
        ),
        required=False,
        metadata={"description": "List of recipient keys"},
    )
    routing_keys = fields.List(
        fields.Str(
            validate=INDY_RAW_PUBLIC_KEY_VALIDATE,
            metadata={
                "description": "Routing key",
                "example": INDY_RAW_PUBLIC_KEY_EXAMPLE,
            },
        ),
        data_key="routingKeys",
        required=False,
        metadata={"description": "List of routing keys"},
    )
    sender_key = fields.Str(
        required=False,
        validate=INDY_RAW_PUBLIC_KEY_VALIDATE,
        metadata={
            "description": "Sender public key",
            "example": INDY_RAW_PUBLIC_KEY_EXAMPLE,
        },
    )
