"""Model for out of band invitations."""

from typing import Any

from marshmallow import fields

from .....messaging.models.base_record import BaseExchangeRecord, BaseExchangeSchema
from .....messaging.valid import UUIDFour


class Invitation(BaseExchangeRecord):
    """Represents an out of band invitation flow."""

    class Meta:
        """Invitation metadata."""

        schema_class = "InvitationSchema"

    RECORD_TYPE = "oob-invitation"
    RECORD_ID_NAME = "invitation_id"
    WEBHOOK_TOPIC = "oob-invitation"

    STATE_INITIAL = "initial"
    STATE_AWAIT_RESPONSE = "await_response"
    STATE_DONE = "done"

    def __init__(
        self,
        *,
        invitation_id: str = None,
        state: str = None,
        invitation: dict = None,
        trace: bool = False,
        **kwargs,
    ):
        """Initialize a new Invitation."""
        super().__init__(invitation_id, state, trace=trace, **kwargs)
        self._id = invitation_id
        self.invitation = invitation
        self.state = state
        self.trace = trace

    def __eq__(self, other: Any) -> bool:
        """Comparison between records."""
        return super().__eq__(other)

    @property
    def invitation_id(self) -> str:
        """Accessor for the ID associated with this exchange."""
        return self._id

    @property
    def record_value(self) -> dict:
        """Accessor for the JSON record value generated for this invitation."""
        return {
            prop: getattr(self, prop)
            for prop in ("invitation_id", "invitation", "state", "trace")
        }


class InvitationSchema(BaseExchangeSchema):
    """Schema to allow serialization/deserialization of invitation records."""

    class Meta:
        """InvitationSchema metadata."""

        model_class = Invitation

    invitation_id = fields.Str(
        required=False, description="Invitation identifier", example=UUIDFour.EXAMPLE,
    )
    state = fields.Str(
        required=False,
        description="Out of band message exchange state",
        example=Invitation.STATE_AWAIT_RESPONSE,
    )
    invitation = fields.Dict(
        required=False, description="Out of band invitation object",
    )
