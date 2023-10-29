"""mediate-grant message.

Used to notify mediation client of a granted mediation request.
"""

from typing import Sequence

from marshmallow import fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from ..message_types import MEDIATE_GRANT, PROTOCOL_PACKAGE
from ..normalization import normalize_from_public_key

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers.mediation_grant_handler.MediationGrantHandler"
)


class MediationGrant(AgentMessage):
    """Class representing a mediation grant message."""

    class Meta:
        """Metadata for a mediation grant."""

        handler_class = HANDLER_CLASS
        message_type = MEDIATE_GRANT
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
            endpoint: Endpoint address for the mediation route
            routing_keys: Keys for the mediation route
        """
        super(MediationGrant, self).__init__(**kwargs)
        self.endpoint = endpoint
        self.routing_keys = (
            list(normalize_from_public_key(key) for key in routing_keys)
            if routing_keys
            else []
        )


class MediationGrantSchema(AgentMessageSchema):
    """Mediation grant schema class."""

    class Meta:
        """Mediation grant schema metadata."""

        model_class = MediationGrant

    endpoint = fields.Str(
        metadata={
            "description": (
                "endpoint on which messages destined for the recipient are received."
            ),
            "example": "http://192.168.56.102:8020/",
        }
    )
    routing_keys = fields.List(
        fields.Str(
            metadata={"description": "Keys to use for forward message packaging"}
        ),
        required=False,
    )
