"""Record used to represent a service block of an out of band invitation."""

from typing import Sequence

from marshmallow import fields

from .....messaging.models.base import BaseModel, BaseModelSchema
from .....messaging.valid import INDY_DID, INDY_RAW_PUBLIC_KEY


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
            recipient_key: A list of recipient keys
            routing_keys: A list of routing keys
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

    _id = fields.Str(required=True, description="", data_key="id")
    _type = fields.Str(required=True, description="", data_key="type")
    did = fields.Str(required=False, description="", **INDY_DID)

    recipient_keys = fields.List(
        fields.Str(description="Recipient public key", **INDY_RAW_PUBLIC_KEY),
        data_key="recipientKeys",
        required=False,
        description="List of recipient keys",
    )

    routing_keys = fields.List(
        fields.Str(description="Routing key", **INDY_RAW_PUBLIC_KEY),
        data_key="routingKeys",
        required=False,
        description="List of routing keys",
    )

    service_endpoint = fields.Str(
        data_key="serviceEndpoint",
        required=False,
        description="Service endpoint at which to reach this agent",
        example="http://192.168.56.101:8020",
    )
