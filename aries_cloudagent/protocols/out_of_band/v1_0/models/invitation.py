"""Record for out of band invitations."""

from typing import Any, Mapping, Union

from marshmallow import fields

from .....messaging.models.base_record import BaseExchangeRecord, BaseExchangeSchema
from .....messaging.valid import UUID4_EXAMPLE
from ..messages.invitation import InvitationMessage, InvitationMessageSchema


class InvitationRecord(BaseExchangeRecord):
    """Represents an out of band invitation record."""

    class Meta:
        """InvitationRecord metadata."""

        schema_class = "InvitationRecordSchema"

    RECORD_TYPE = "oob_invitation"
    RECORD_ID_NAME = "invitation_id"
    RECORD_TOPIC = "oob_invitation"
    TAG_NAMES = {"invi_msg_id"}

    STATE_INITIAL = "initial"
    STATE_AWAIT_RESPONSE = "await_response"
    STATE_DONE = "done"

    def __init__(
        self,
        *,
        invitation_id: str = None,
        state: str = None,
        invi_msg_id: str = None,
        invitation: Union[InvitationMessage, Mapping] = None,  # invitation message
        invitation_url: str = None,
        oob_id: str = None,
        public_did: str = None,  # backward-compat: BaseRecord.from_storage()
        trace: bool = False,
        **kwargs,
    ):
        """Initialize a new InvitationRecord."""
        super().__init__(invitation_id, state, trace=trace, **kwargs)
        self._id = invitation_id
        self.state = state
        self.invi_msg_id = invi_msg_id
        self._invitation = InvitationMessage.serde(invitation)
        self.invitation_url = invitation_url
        self.oob_id = oob_id
        self.trace = trace

    @property
    def invitation_id(self) -> str:
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
                for prop in ("invitation_url", "state", "trace", "oob_id")
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


class InvitationRecordSchema(BaseExchangeSchema):
    """Schema to allow serialization/deserialization of invitation records."""

    class Meta:
        """InvitationRecordSchema metadata."""

        model_class = InvitationRecord

    invitation_id = fields.Str(
        required=False,
        metadata={
            "description": "Invitation record identifier",
            "example": UUID4_EXAMPLE,
        },
    )
    state = fields.Str(
        required=False,
        metadata={
            "description": "Out of band message exchange state",
            "example": InvitationRecord.STATE_AWAIT_RESPONSE,
        },
    )
    invi_msg_id = fields.Str(
        required=False,
        metadata={
            "description": "Invitation message identifier",
            "example": UUID4_EXAMPLE,
        },
    )
    oob_id = fields.Str(
        required=False,
        metadata={
            "description": "Out of band record identifier",
            "example": UUID4_EXAMPLE,
        },
    )
    invitation = fields.Nested(
        InvitationMessageSchema(),
        required=False,
        metadata={"description": "Out of band invitation message"},
    )
    invitation_url = fields.Str(
        required=False,
        metadata={
            "description": "Invitation message URL",
            "example": (
                "https://example.com/endpoint?c_i=eyJAdHlwZSI6ICIuLi4iLCAiLi4uIjog"
                "Ii4uLiJ9XX0="
            ),
        },
    )
