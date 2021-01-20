"""Record for connection reuse messages."""

from typing import Any

from marshmallow import fields

from .....messaging.models.base_record import BaseRecord, BaseRecordSchema
from .....messaging.valid import UUIDFour


class ConnReuseMessageRecord(BaseRecord):
    """Represents a connection reuse record."""

    class Meta:
        """ConnReuseMessageRecord metadata."""

        schema_class = "ConnReuseMessageRecordSchema"

    RECORD_TYPE = "conn_reuse_msg"
    RECORD_ID_NAME = "conn_reuse_msg_id"
    TAG_NAMES = {"invi_msg_id", "conn_rec_id"}

    STATE_INITIAL = "initial"
    STATE_NOT_ACCEPTED = "not_accepted"
    STATE_ACCEPTED = "accepted"

    def __init__(
        self,
        *,
        state: str = None,
        conn_reuse_msg_id: str = None,
        conn_rec_id: str = None,
        invi_msg_id: str = None,
        **kwargs,
    ):
        """Initialize a new InvitationRecord."""
        super().__init__(conn_reuse_msg_id, invi_msg_id, conn_rec_id, state, **kwargs)
        self._id = conn_reuse_msg_id
        self.invi_msg_id = invi_msg_id
        self.state = state
        self.conn_rec_id = conn_rec_id

    def __eq__(self, other: Any) -> bool:
        """Comparison between records."""
        return super().__eq__(other)

    @property
    def conn_reuse_msg_id(self) -> str:
        """Accessor for the ID associated with conn_reuse_msg record."""
        return self._id

    @property
    def record_value(self) -> dict:
        """Accessor for the JSON record value generated for this invitation."""
        return {
            prop: getattr(self, prop)
            for prop in (
                "state",
                "invi_msg_id",
                "conn_rec_id",
            )
        }


class ConnReuseMessageRecordSchema(BaseRecordSchema):
    """Schema to allow serialization/deserialization of invitation records."""

    class Meta:
        """InvitationRecordSchema metadata."""

        model_class = ConnReuseMessageRecord

    conn_reuse_msg_id = fields.Str(
        required=False,
        description="ConnReuseMessage record identifier",
        example=UUIDFour.EXAMPLE,
    )
    invi_msg_id = fields.Str(
        required=False,
        description="Invitation message identifier",
        example=UUIDFour.EXAMPLE,
    )
    conn_rec_id = fields.Str(
        required=False,
        description="ConnRecord identifier",
        example=UUIDFour.EXAMPLE,
    )
    state = fields.Str(
        required=False,
        description="Connection reuse message state",
        example=ConnReuseMessageRecord.STATE_INITIAL,
    )
