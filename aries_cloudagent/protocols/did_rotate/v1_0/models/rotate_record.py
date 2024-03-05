"""RotateRecord model."""

from typing import Optional

from marshmallow import EXCLUDE, fields, validate

from .....messaging.models.base_record import BaseRecord, BaseRecordSchema


class RotateRecord(BaseRecord):
    """RotateRecord model.

    Stores state of a single DID rotate message exchange.
    """

    class Meta:
        """RotateRecord metadata."""

        schema_class = "RotateRecordSchema"

    RECORD_TYPE = "did_rotate"
    RECORD_ID_NAME = "record_id"

    # Role values
    ROLE_ROTATING = "rotating"
    ROLE_OBSERVING = "observing"

    # State values
    STATE_ROTATE_SENT = "rotate-sent"
    STATE_ROTATE_RECEIVED = "rotate-received"
    STATE_ACK_SENT = "ack-sent"
    STATE_ACK_RECEIVED = "ack-received"
    STATE_FAILED = "failed"

    TAG_NAMES = {"connection_id", "state", "role", "thread_id"}

    def __init__(
        self,
        *,
        record_id: Optional[str] = None,
        role: Optional[str] = None,
        state: Optional[str] = None,
        connection_id: Optional[str] = None,
        error: Optional[str] = None,
        new_did: Optional[str] = None,
        thread_id: Optional[str] = None,
        **kwargs,
    ):
        """Initialize a new RotateRecord."""
        super().__init__(record_id, state or self.STATE_ROTATE_SENT, **kwargs)
        self.role = role or self.ROLE_ROTATING
        self.connection_id = connection_id
        self.new_did = new_did
        self.thread_id = thread_id
        self.error = error

    @property
    def record_id(self) -> str:
        """Accessor for the ID associated with this record."""
        return self._id

    @classmethod
    async def retrieve_by_connection_id(
        cls, session, connection_id: str
    ) -> "RotateRecord":
        """Retrieve a rotate record by connection ID."""
        return await cls.retrieve_by_tag_filter(
            session, {"connection_id": connection_id}
        )

    @classmethod
    async def retrieve_by_thread_id(cls, session, thread_id: str) -> "RotateRecord":
        """Retrieve a rotate record by thread ID."""
        return await cls.retrieve_by_tag_filter(session, {"thread_id": thread_id})

    @property
    def record_value(self) -> dict:
        """Accessor to for the JSON record value properties."""
        return {
            prop: getattr(self, prop)
            for prop in (
                "role",
                "state",
                "connection_id",
                "error",
                "new_did",
                "thread_id",
            )
        }


class RotateRecordSchema(BaseRecordSchema):
    """RotateRecord schema."""

    class Meta:
        """RotateRecordSchema metadata."""

        model_class = RotateRecord
        unknown = EXCLUDE

    record_id = fields.Str(required=True, metadata={"description": "Record identifier"})
    role = fields.Str(
        required=True,
        metadata={
            "description": "Role in the DID rotate protocol: rotating or observing"
        },
        validate=validate.OneOf(
            [RotateRecord.ROLE_ROTATING, RotateRecord.ROLE_OBSERVING]
        ),
    )
    state = fields.Str(
        required=True,
        metadata={
            "description": (
                "State of the DID rotate protocol: rotate-sent, rotate-received, "
                "ack-sent, ack-received, or failed"
            )
        },
        validate=validate.OneOf(
            [
                RotateRecord.STATE_ROTATE_SENT,
                RotateRecord.STATE_ROTATE_RECEIVED,
                RotateRecord.STATE_ACK_SENT,
                RotateRecord.STATE_ACK_RECEIVED,
                RotateRecord.STATE_FAILED,
            ]
        ),
    )
    connection_id = fields.Str(
        required=True,
        metadata={
            "description": "Connection identifier",
            "example": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        },
    )
    error = fields.Str(
        required=False,
        metadata={"description": "Error message", "example": "Invalid DID"},
    )
    new_did = fields.Str(
        required=False,
        metadata={
            "description": "New DID",
            "example": "did:sov:WRfXPg8dantKVubE3HX8pw",
        },
    )
