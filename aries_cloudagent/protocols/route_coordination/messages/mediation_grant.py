"""Mediation grant message."""

from typing import Sequence

from marshmallow import fields

from ....messaging.agent_message import AgentMessage, AgentMessageSchema
from ..message_types import MEDIATION_GRANT, PROTOCOL_PACKAGE

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers"
    ".mediation_grant_handler.MediationGrantHandler"
)


class MediationGrant(AgentMessage):
    """Class representing a mediation grant message."""

    class Meta:
        """Metadata for a mediation grant."""

        handler_class = HANDLER_CLASS
        message_type = MEDIATION_GRANT
        schema_class = "MediationGrantSchema"

    def __init__(
        self,
        *,
        endpoint: str = None,
        routing_keys: Sequence[str] = None,
        **kwargs,
    ):
        """
        Initialize mediation grant object.

        Args:
            endpoint: Endpoint adress for the mediation route
            routing_keys: Keys for the mediation route
        """
        super(MediationGrant, self).__init__(**kwargs)
        self.endpoint = endpoint
        self.routing_keys = list(routing_keys) if routing_keys else []


class MediationGrantSchema(AgentMessageSchema):
    """Mediation grant schema class."""

    class Meta:
        """Mediation grant schema metadata."""

        model_class = MediationGrant

    endpoint = fields.Str(
            description="Route coordination specific endpoint",
            example="http://192.168.56.102:8020/r/3fa85f64-5717-4562-b3fc-2c963f66afa6"
        )
    routing_keys = fields.List(
        fields.Str(
            description="Assigned routing keys"
        ),
        required=False,
    )
