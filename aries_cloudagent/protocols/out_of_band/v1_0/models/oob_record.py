"""Record for out of band invitations."""

from typing import Any, Mapping, Optional, Union

from marshmallow import fields

from .....messaging.decorators.service_decorator import (
    ServiceDecorator,
    ServiceDecoratorSchema,
)

from .....messaging.models.base_record import BaseExchangeRecord, BaseExchangeSchema
from .....messaging.valid import UUIDFour

from ..messages.invitation import InvitationMessage, InvitationMessageSchema


class OobRecord(BaseExchangeRecord):
    """Represents an out of band record."""

    class Meta:
        """OobRecord metadata."""

        schema_class = "OobRecordSchema"

    RECORD_TYPE = "oob_record"
    RECORD_ID_NAME = "oob_id"
    RECORD_TOPIC = "out_of_band"
    TAG_NAMES = {
        "invi_msg_id",
        "attach_thread_id",
        "our_recipient_key",
        "connection_id",
        "reuse_msg_id",
    }

    STATE_INITIAL = "initial"
    STATE_PREPARE_RESPONSE = "prepare-response"
    STATE_AWAIT_RESPONSE = "await-response"
    STATE_NOT_ACCEPTED = "reuse-not-accepted"
    STATE_ACCEPTED = "reuse-accepted"
    STATE_DONE = "done"

    ROLE_SENDER = "sender"
    ROLE_RECEIVER = "receiver"

    def __init__(
        self,
        *,
        state: str,
        invi_msg_id: str,
        role: str,
        invitation: Union[InvitationMessage, Mapping[str, Any]],
        their_service: Optional[ServiceDecorator] = None,
        connection_id: Optional[str] = None,
        reuse_msg_id: Optional[str] = None,
        oob_id: Optional[str] = None,
        attach_thread_id: Optional[str] = None,
        our_recipient_key: Optional[str] = None,
        our_service: Optional[ServiceDecorator] = None,
        multi_use: bool = False,
        trace: bool = False,
        **kwargs,
    ):
        """Initialize a new OobRecord."""
        super().__init__(oob_id, state, trace=trace, **kwargs)
        self._id = oob_id
        self.state = state
        self.invi_msg_id = invi_msg_id
        self.role = role
        self._invitation = InvitationMessage.serde(invitation)
        self.connection_id = connection_id
        self.reuse_msg_id = reuse_msg_id
        self.their_service = their_service
        self.our_service = our_service
        self.attach_thread_id = attach_thread_id
        self.our_recipient_key = our_recipient_key
        self.multi_use = multi_use
        self.trace = trace

    @property
    def oob_id(self) -> str:
        """Accessor for the ID associated with this exchange."""
        return self._id

    @property
    def invitation(self) -> InvitationMessage:
        """Accessor; get deserialized view."""
        return None if self._invitation is None else self._invitation.de

    @invitation.setter
    def invitation(self, value):
        """Setter; store de/serialized views."""
        self._invitation = InvitationMessage.serde(value)

    @property
    def record_value(self) -> dict:
        """Accessor for the JSON record value generated for this invitation."""
        return {
            **{
                prop: getattr(self, prop)
                for prop in (
                    "state",
                    "their_service",
                    "connection_id",
                    "role",
                    "our_service",
                )
            },
            **{
                prop: getattr(self, f"_{prop}").ser
                for prop in ("invitation",)
                if getattr(self, prop) is not None
            },
        }

    def __eq__(self, other: Any) -> bool:
        """Comparison between records."""
        return super().__eq__(other)


class OobRecordSchema(BaseExchangeSchema):
    """Schema to allow serialization/deserialization of invitation records."""

    class Meta:
        """OobRecordSchema metadata."""

        model_class = OobRecord

    oob_id = fields.Str(
        required=True,
        description="Oob record identifier",
        example=UUIDFour.EXAMPLE,
    )
    state = fields.Str(
        required=True,
        description="Out of band message exchange state",
        example=OobRecord.STATE_AWAIT_RESPONSE,
    )
    invi_msg_id = fields.Str(
        required=True,
        description="Invitation message identifier",
        example=UUIDFour.EXAMPLE,
    )
    invitation = fields.Nested(
        InvitationMessageSchema(),
        required=True,
        description="Out of band invitation message",
    )

    their_service = fields.Nested(
        ServiceDecoratorSchema(),
        required=False,
    )

    connection_id = fields.Str(
        description="Connection record identifier",
        required=False,
        example=UUIDFour.EXAMPLE,
    )

    attach_thread_id = fields.Str(
        description="Connection record identifier",
        required=False,
        example=UUIDFour.EXAMPLE,
    )

    our_recipient_key = fields.Str(
        description="Recipient key used for oob invitation",
        required=False,
        example=UUIDFour.EXAMPLE,
    )

    role = fields.Str(
        description="OOB Role",
        required=False,
        example=OobRecord.ROLE_RECEIVER,
    )
