"""Route coordination record information with non-secrets storage."""

from typing import Sequence

from marshmallow import fields
from marshmallow.validate import OneOf

from ....config.injection_context import InjectionContext
from ....messaging.models.base_record import BaseRecord, BaseRecordSchema
from ....messaging.valid import UUIDFour


class RouteCoordination(BaseRecord):  # lgtm[py/missing-equals]
    """Represents a route coordination for coordinate mediation."""

    class Meta:
        """RouteCoordination metadata."""

        schema_class = "RouteCoordinationSchema"

    RECORD_TYPE = "route_coordination"
    RECORD_ID_NAME = "route_coordination_id"
    WEBHOOK_TOPIC = "route_coordination"
    TAG_NAMES = {
        "connection_id",
        "routing_endpoint",
        "thread_id",
    }

    STATE_MEDIATION_REQUEST = "mediation_request"
    STATE_MEDIATION_SENT = "mediation_sent"
    STATE_MEDIATION_RECEIVED = "mediation_request_received"
    STATE_MEDIATION_GRANTED = "mediation_granted"
    STATE_MEDIATION_DENIED = "mediation_denied"
    STATE_MEDIATION_CANCELED = "mediation_canceled"

    INITIATOR_SELF = "self"
    INITIATOR_EXTERNAL = "external"

    ROLE_MEDIATOR = "mediator"
    ROLE_RECIPIENT = "recipient"

    def __init__(
        self,
        *,
        route_coordination_id: str = None,
        connection_id: str = None,
        thread_id: str = None,
        initiator: str = None,
        role: str = None,
        state: str = None,
        mediator_terms: Sequence[str] = None,
        recipient_terms: Sequence[str] = None,
        routing_keys: Sequence[str] = None,
        routing_endpoint: str = None,
        error_msg: str = None,
        **kwargs,
    ):
        """Initialize a new RouteCoordination."""
        super().__init__(route_coordination_id, state, **kwargs)
        self._id = route_coordination_id
        self.connection_id = connection_id
        self.thread_id = thread_id
        self.initiator = initiator
        self.role = role
        self.state = state
        self.mediator_terms = list(mediator_terms) if mediator_terms else []
        self.recipient_terms = list(recipient_terms) if recipient_terms else []
        self.routing_keys = list(routing_keys) if routing_keys else []
        self.routing_endpoint = routing_endpoint
        self.error_msg = error_msg

    @property
    def route_coordination_id(self) -> str:
        """Accessor for the ID associated with this route coordination."""
        return self._id

    @property
    def record_value(self) -> dict:
        """Accessor for the JSON record value generated for this route coordination."""
        return {
            prop: getattr(self, prop)
            for prop in (
                "connection_id",
                "state",
                "mediator_terms",
                "recipient_terms",
                "routing_keys",
                "routing_endpoint",
                "role"
            )
        }

    @classmethod
    async def retrieve_by_thread(
        cls, context: InjectionContext, thread_id: str
    ) -> "RouteCoordination":
        """Retrieve a route coordination record by thread ID."""
        record = await cls.retrieve_by_tag_filter(
            context, {"thread_id": thread_id}
        )
        return record

    @classmethod
    async def retrieve_by_connection_id(
        cls, context: InjectionContext, connection_id: str
    ) -> "RouteCoordination":
        """Retrieve a route coordination record by connection id."""
        record = await cls.retrieve_by_tag_filter(
            context, {"connection_id": connection_id}
        )
        return record


class RouteCoordinationSchema(BaseRecordSchema):
    """Schema to allow serialization/deserialization of route coordination records."""

    class Meta:
        """RouteCoordinationSchema metadata."""

        model_class = RouteCoordination

    route_coordination_id = fields.Str(
        required=False,
        description="Route coordination identifier",
        example=UUIDFour.EXAMPLE,
    )
    connection_id = fields.Str(
        required=False, description="Connection identifier", example=UUIDFour.EXAMPLE
    )
    thread_id = fields.Str(
        required=False, description="Thread identifier", example=UUIDFour.EXAMPLE
    )
    state = fields.Str(
        required=False,
        description="Mediator process state",
        example=RouteCoordination.STATE_MEDIATION_REQUEST,
    )
    mediator_terms = fields.List(
        fields.Str(
            description="Indicate terms that the mediator "
            "requires the recipient to agree to"
        ),
        required=False,
        description="List of mediator rules for recipient",
    )
    recipient_terms = fields.List(
        fields.Str(
            description="Indicate terms that the recipient "
            "requires the mediator to agree to"
        ),
        required=False,
        description="List of mediator rules for mediator",
    )
    routing_keys = fields.List(
        fields.Str(
            description="Recipient verkeys for routing"
        ),
        required=False,
        description="List of all related verkeys for the routing",
    )
    routing_endpoint = fields.Str(
        required=False,
        description="Mediation routing endpoint",
        example="http://192.168.56.102:8020/r/3fa85f64-5717-4562-b3fc-2c963f66afa6",
    )
    error_msg = fields.Str(
        required=False,
        description="Error message",
        example="-",
    )
    initiator = fields.Str(
        required=False,
        description="Routing protocol initiator: self or external",
        example=RouteCoordination.INITIATOR_SELF,
        validate=OneOf(["self", "external"]),
    )
    role = fields.Str(
        required=False,
        description="Routing protocol role: mediator or recipient",
        example=RouteCoordination.ROLE_MEDIATOR,
        validate=OneOf(["mediator", "recipient"]),
    )
