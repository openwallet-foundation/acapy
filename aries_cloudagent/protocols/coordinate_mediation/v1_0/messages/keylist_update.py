"""keylist-update message used to notify mediator of keylist changes."""

from typing import Sequence

from marshmallow import fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from ..message_types import KEYLIST_UPDATE, PROTOCOL_PACKAGE

from .inner.keylist_update_rule import KeylistUpdateRule, KeylistUpdateRuleSchema

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers.keylist_update_handler.KeylistUpdateHandler"
)


class KeylistUpdate(AgentMessage):
    """Class representing a keylist update message."""

    class Meta:
        """Metadata for a keylist update."""

        handler_class = HANDLER_CLASS
        message_type = KEYLIST_UPDATE
        schema_class = "KeylistUpdateSchema"

    def __init__(
        self,
        *,
        updates: Sequence[KeylistUpdateRule] = None,
        **kwargs,
    ):
        """
        Initialize keylist update object.

        Args:
            updates: Update rules for keylist update request
        """
        super(KeylistUpdate, self).__init__(**kwargs)
        self.updates = list(updates) if updates else []


class KeylistUpdateSchema(AgentMessageSchema):
    """Keylist update schema class."""

    class Meta:
        """Keylist update schema metadata."""

        model_class = KeylistUpdate

    updates = fields.List(
        fields.Nested(KeylistUpdateRuleSchema()),
        description="List of update rules",
    )
