"""Record used to represent a service block of an out of band invitation."""

from typing import Sequence

from marshmallow import EXCLUDE, fields, post_dump

from .....messaging.models.base import BaseModel, BaseModelSchema
from .....messaging.valid import (
    DID_KEY_EXAMPLE,
    DID_KEY_VALIDATE,
    INDY_DID_EXAMPLE,
    INDY_DID_VALIDATE,
)


class Service(BaseModel):
    """Record used to represent a service block of an out of band invitation."""

    class Meta:
        """Service metadata."""

        schema_class = "ServiceSchema"

    def __init__(
        self,
        *,
        _id: str = None,
        _type: str = None,
        did: str = None,
        recipient_keys: Sequence[str] = None,
        routing_keys: Sequence[str] = None,
        service_endpoint: str = None,
    ):
        """
        Initialize a Service instance.

        Args:
            id: An identifier for this service block
            type: A type for this service block
            did: A did for the connection
            recipient_key: A list of recipient keys in W3C did:key format
            routing_keys: A list of routing keys in W3C did:key format
            service_endpoint: An endpoint for the connection
        """
        self._id = _id
        self._type = _type
        self.did = did
        self.recipient_keys = list(recipient_keys) if recipient_keys else []
        self.routing_keys = list(routing_keys) if routing_keys else []
        self.service_endpoint = service_endpoint


class ServiceSchema(BaseModelSchema):
    """Service schema."""

    class Meta:
        """ServiceSchema metadata."""

        model_class = Service
        unknown = EXCLUDE

    _id = fields.Str(
        required=True, data_key="id", metadata={"description": "Service identifier"}
    )
    _type = fields.Str(
        required=True, data_key="type", metadata={"description": "Service type"}
    )
    did = fields.Str(
        required=False,
        validate=INDY_DID_VALIDATE,
        metadata={"description": "Service DID", "example": INDY_DID_EXAMPLE},
    )

    recipient_keys = fields.List(
        fields.Str(
            validate=DID_KEY_VALIDATE,
            metadata={
                "description": "Recipient public key",
                "example": DID_KEY_EXAMPLE,
            },
        ),
        data_key="recipientKeys",
        required=False,
        metadata={"description": "List of recipient keys"},
    )

    routing_keys = fields.List(
        fields.Str(
            validate=DID_KEY_VALIDATE,
            metadata={"description": "Routing key", "example": DID_KEY_EXAMPLE},
        ),
        data_key="routingKeys",
        required=False,
        metadata={"description": "List of routing keys"},
    )

    service_endpoint = fields.Str(
        data_key="serviceEndpoint",
        required=False,
        metadata={
            "description": "Service endpoint at which to reach this agent",
            "example": "http://192.168.56.101:8020",
        },
    )

    @post_dump
    def post_dump(self, data, **kwargs):
        """Post dump hook."""

        if "routingKeys" in data and not data["routingKeys"]:
            del data["routingKeys"]

        return data
