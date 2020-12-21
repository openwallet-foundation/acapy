"""Represents a Transaction role to send message."""

from marshmallow import EXCLUDE, fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema

from ..message_types import TRANSACTION_ROLE_TO_SEND, PROTOCOL_PACKAGE

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers"
    ".transaction_role_to_send_handler.TransactionRoleToSendHandler"
)


class TransactionRoleToSend(AgentMessage):
    """Class representing a transaction role to send."""

    class Meta:
        """Metadata for a TransactionRoleToSend."""

        handler_class = HANDLER_CLASS
        message_type = TRANSACTION_ROLE_TO_SEND
        schema_class = "TransactionRoleToSendSchema"

    def __init__(
        self,
        *,
        role: str = None,
        **kwargs,
    ):
        """
        Initialize transaction role to send.

        Args:
            role: The role that needs to be send

        """

        super().__init__(**kwargs)
        self.role = role


class TransactionRoleToSendSchema(AgentMessageSchema):
    """Transaction Role to send schema class."""

    class Meta:
        """Metadata for a TransactionRoleToSendSchema."""

        model_class = TransactionRoleToSend
        unknown = EXCLUDE

    role = fields.Str(
        required=True,
        description="Transaction Role that is sent to the other agent",
        example="TRANSACTION_AUTHOR",
    )
