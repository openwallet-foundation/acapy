"""Routing term record for route coordination."""

from marshmallow import fields
from marshmallow.validate import OneOf

from ....messaging.models.base_record import BaseRecord, BaseRecordSchema
from ....messaging.valid import UUIDFour


class RoutingTerm(BaseRecord):  # lgtm[py/missing-equals]
    """Represents a routing term for coordinate mediation."""

    class Meta:
        """RoutingTerm metadata."""

        schema_class = "RoutingTermSchema"

    RECORD_TYPE = "routing_term"
    RECORD_ID_NAME = "routing_term_id"
    WEBHOOK_TOPIC = "routing_term"
    TAG_NAMES = {
        "route_coordination_id",
    }

    OWNER_MEDIATOR = "mediator"
    OWNER_RECIPIENT = "recipient"

    def __init__(
        self,
        *,
        routing_term_id: str = None,
        route_coordination_id: str = None,
        term: str = None,
        owner: str = None,
        error_msg: str = None,
        **kwargs,
    ):
        """Initialize a new RoutingTerm."""
        super().__init__(routing_term_id, None, **kwargs)
        self._id = routing_term_id
        self.route_coordination_id = route_coordination_id
        self.term = term
        self.owner = owner
        self.error_msg = error_msg

    @property
    def routing_term_id(self) -> str:
        """Accessor for the ID associated with this route key."""
        return self._id

    @property
    def record_value(self) -> dict:
        """Accessor for the JSON record value generated for this route coordination."""
        return {
            prop: getattr(self, prop)
            for prop in (
                "route_coordination_id",
                "owner",
                "term"
            )
        }


class RoutingTermSchema(BaseRecordSchema):
    """Schema to allow serialization/deserialization of routing term records."""

    class Meta:
        """RoutingTermSchema metadata."""

        model_class = RoutingTerm
    routing_term_id = fields.Str(
        required=False,
        description="Routing term identifier",
        example=UUIDFour.EXAMPLE,
    )
    route_coordination_id = fields.Str(
        required=False,
        description="Route coordination reference for recotd",
        example=UUIDFour.EXAMPLE,
    )
    term = fields.Str(
        required=False,
        description="Term content of term",
    )
    owner = fields.Str(
        required=False,
        description="Owner of the routing term",
        example=RoutingTerm.OWNER_RECIPIENT,
        validate=OneOf(["mediator", "recipient"]),
    )
