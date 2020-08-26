"""Aries#0023 DID exchange model."""

from marshmallow import fields, validate

from .....messaging.models.base_record import BaseRecord, BaseExchangeSchema
from .....messaging.valid import UUIDFour


class DIDExchange(BaseRecord):
    """Represents an Aries#0023 did exchange."""

    class Meta:
        """DIDExchange metadata."""

        schema_class = "DIDExchangeSchema"

    RECORD_TYPE = "did_exchange"
    RECORD_ID_NAME = "did_exchange_id"
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
        did_exchange_id: str = None,
        initiator: str = None,
        state: str = None,
        error_msg: str = None,
        trace: bool = False,
        **kwargs,
    ):
        """Initialize a new DIDExchange."""
        super().__init__(did_exchange_id, state, trace=trace, **kwargs)
        self._id = did_exchange_id
        self.initiator = initiator
        self.state = state
        self.error_msg = error_msg
        self.trace = trace

    @property
    def did_exchange_id(self) -> str:
        """Accessor for the ID associated with this exchange."""
        return self._id

    @property
    def record_value(self) -> dict:
        """Accessor for the JSON record value generated for this did exchange."""
        return {
            prop: getattr(self, prop)
            for prop in ("error_msg", "initiator", "role", "state", "trace",)
        }


class DIDExchangeSchema(BaseExchangeSchema):
    """Schema to allow serialization/deserialization of did exchange records."""

    class Meta:
        """DIDExchangeSchema metadata."""

        model_class = DIDExchange

    did_exchange_id = fields.Str(
        required=False, description="DID exchange identifier", example=UUIDFour.EXAMPLE,
    )
    initiator = fields.Str(
        required=False,
        description="DID exchange initiator: self or external",
        example=DIDExchange.INITIATOR_SELF,
        validate=validate.OneOf(["self", "external"]),
    )
    state = fields.Str(
        required=False,
        description="DID exchange state",
        example=DIDExchange.STATE_REPONSE_RECEIVED,
    )
    error_msg = fields.Str(
        required=False,
        description="Error message",
        example="credential definition identifier is not set in proposal",
    )
