"""Aries#0023 DID exchange model."""

from marshmallow import fields, validate

from .....messaging.models.base_record import BaseRecord, BaseExchangeSchema
from .....messaging.valid import UUIDFour


class DIDExRecord(BaseRecord):
    """Represents an Aries#0023 did exchange."""

    class Meta:
        """DIDExRecord metadata."""

        schema_class = "DIDExRecordSchema"

    RECORD_TYPE = "did_exchange"
    RECORD_ID_NAME = "did_ex_id"
    WEBHOOK_TOPIC = "did_exchange"

    ROLE_REQUESTER = "requester"
    ROLE_RESPONDER = "responder"

    STATE_START = "start"
    STATE_INVITATION_SENT = "invitation-sent"
    STATE_INVITATION_RECEIVED = "invitation-received"
    STATE_REQUEST_SENT = "request-sent"
    STATE_REQUEST_RECEIVED = "request-received"
    STATE_RESPONSE_SENT = "response-sent"
    STATE_REPONSE_RECEIVED = "response-received"
    STATE_ABANDONED = "abandoned"
    STATE_COMPLETED = "completed"

    def __init__(
        self,
        *,
        did_ex_id: str = None,
        role: str = None,
        state: str = None,
        error_msg: str = None,
        trace: bool = False,
        **kwargs,
    ):
        """Initialize a new DIDExRecord."""
        super().__init__(did_ex_id, state, trace=trace, **kwargs)
        self._id = did_ex_id
        self.role = role
        self.state = state
        self.error_msg = error_msg
        self.trace = trace

    @property
    def did_ex_id(self) -> str:
        """Accessor for the ID associated with this exchange."""
        return self._id

    @property
    def record_value(self) -> dict:
        """Accessor for the JSON record value generated for this did exchange."""
        return {
            prop: getattr(self, prop)
            for prop in ("error_msg", "role", "state", "trace",)
        }


class DIDExRecordSchema(BaseExchangeSchema):
    """Schema to allow serialization/deserialization of did exchange records."""

    class Meta:
        """DIDExRecordSchema metadata."""

        model_class = DIDExRecord

    did_ex_id = fields.Str(
        required=False, description="DID exchange identifier", example=UUIDFour.EXAMPLE,
    )
    role = fields.Str(
        required=False,
        description="DID exchange role: requester or responder",
        example=DIDExRecord.ROLE_REQUESTER,
        validate=validate.OneOf(
            [
                getattr(DIDExRecord, m)
                for m in vars(DIDExRecord)
                if m.startswith("ROLE_")
            ]
        )
    )
    state = fields.Str(
        required=False,
        description="DID exchange state",
        example=DIDExRecord.STATE_REPONSE_RECEIVED,
    )
    error_msg = fields.Str(
        required=False,
        description="Error message",
        example="Credential definition identifier is not set in proposal",
    )
