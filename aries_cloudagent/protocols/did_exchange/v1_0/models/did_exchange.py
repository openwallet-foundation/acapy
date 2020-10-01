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

    INITIATOR_SELF = "self"
    INITIATOR_EXTERNAL = "external"

    STATE_START = "start"
    STATE_REQUEST_SENT = "request-sent"
    STATE_REQUEST_RECEIVED = "request-received"
    STATE_RESPONSE_SENT = "response-sent"
    STATE_REPONSE_RECEIVED = "response-received"

    def __init__(
        self,
        *,
        did_ex_id: str = None,
        initiator: str = None,
        state: str = None,
        error_msg: str = None,
        trace: bool = False,
        **kwargs,
    ):
        """Initialize a new DIDExRecord."""
        super().__init__(did_ex_id, state, trace=trace, **kwargs)
        self._id = did_ex_id
        self.initiator = initiator
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
            for prop in ("error_msg", "initiator", "role", "state", "trace",)
        }


class DIDExRecordSchema(BaseExchangeSchema):
    """Schema to allow serialization/deserialization of did exchange records."""

    class Meta:
        """DIDExRecordSchema metadata."""

        model_class = DIDExRecord

    did_ex_id = fields.Str(
        required=False, description="DID exchange identifier", example=UUIDFour.EXAMPLE,
    )
    initiator = fields.Str(
        required=False,
        description="DID exchange initiator: self or external",
        example=DIDExRecord.INITIATOR_SELF,
        validate=validate.OneOf(["self", "external"]),
    )
    state = fields.Str(
        required=False,
        description="DID exchange state",
        example=DIDExRecord.STATE_REPONSE_RECEIVED,
    )
    error_msg = fields.Str(
        required=False,
        description="Error message",
        example="credential definition identifier is not set in proposal",
    )
