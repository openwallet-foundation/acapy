"""Response to keylist-update used to notify mediation client of applied updates."""

from typing import Sequence

from marshmallow import fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from ..message_types import KEYLIST_UPDATE_RESPONSE, PROTOCOL_PACKAGE

from .inner.keylist_updated import KeylistUpdated, KeylistUpdatedSchema

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers"
    ".keylist_update_response_handler.KeylistUpdateResponseHandler"
)


class KeylistUpdateResponse(AgentMessage):
    """Class representing a keylist update result message."""

    class Meta:
        """Metadata for a keylist update result."""

        handler_class = HANDLER_CLASS
        message_type = KEYLIST_UPDATE_RESPONSE
        schema_class = "KeylistUpdateResponseSchema"

    def __init__(
        self,
        *,
        updated: Sequence[KeylistUpdated] = None,
        **kwargs,
    ):
        """
        Initialize keylist update object.

        Args:
            updates: Update rules for keylist update request
        """
        super(KeylistUpdateResponse, self).__init__(**kwargs)
        self.updated = list(updated) if updated else []


class KeylistUpdateResponseSchema(AgentMessageSchema):
    """Keylist update result schema class."""

    class Meta:
        """Keylist update result schema metadata."""

        model_class = KeylistUpdateResponse

    updated = fields.List(
        fields.Nested(KeylistUpdatedSchema()),
        description="List of update results for each update",
    )
