"""Routing key record for route coordination."""

from marshmallow import fields

from ....messaging.models.base_record import BaseRecord, BaseRecordSchema
from ....messaging.valid import UUIDFour, INDY_RAW_PUBLIC_KEY


class RoutingKey(BaseRecord):  # lgtm[py/missing-equals]
    """Represents a routing key for specific route coordination."""

    class Meta:
        """RoutingKey metadata."""

        schema_class = "RoutingKeySchema"

    RECORD_TYPE = "routing_key"
    RECORD_ID_NAME = "routing_key_id"
    WEBHOOK_TOPIC = "routing_key"
    TAG_NAMES = {
        "routing_key",
        "route_coordination_id",
    }

    def __init__(
        self,
        *,
        routing_key_id: str = None,
        route_coordination_id: str = None,
        routing_key: str = None,
        error_msg: str = None,
        **kwargs,
    ):
        """Initialize a new RouteCoordination."""
        super().__init__(routing_key_id, None, **kwargs)
        self._id = routing_key_id
        self.route_coordination_id = route_coordination_id
        self.routing_key = routing_key
        self.error_msg = error_msg

    @property
    def routing_key_id(self) -> str:
        """Accessor for the ID associated with this routing key."""
        return self._id

    @property
    def record_value(self) -> dict:
        """Accessor for the JSON record value generated for this routing key."""
        return {
            prop: getattr(self, prop)
            for prop in (
                "routing_key_id",
                "route_coordination_id",
                "routing_key",
            )
        }


class RoutingKeySchema(BaseRecordSchema):
    """Schema to allow serialization/deserialization of route keys."""

    class Meta:
        """RoutingKeySchema metadata."""

        model_class = RoutingKey

    routing_key_id = fields.Str(
        required=False,
        description="Routing key identifier",
        example=UUIDFour.EXAMPLE,
    )
    route_coordination_id = fields.Str(
        required=False,
        description="Route coordination reference key for routing key",
        example=UUIDFour.EXAMPLE,
    )
    routing_key = fields.Str(
        required=False,
        description="Routing key identifier",
        **INDY_RAW_PUBLIC_KEY,
    )
