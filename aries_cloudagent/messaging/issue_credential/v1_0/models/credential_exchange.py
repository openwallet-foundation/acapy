"""Aries#0036 v1.0 credential exchange information with non-secrets storage."""

from marshmallow import fields

from ....models.base_record import BaseRecord, BaseRecordSchema


class V10CredentialExchange(BaseRecord):
    """Represents an Aries#0036 credential exchange."""

    class Meta:
        """CredentialExchange metadata."""

        schema_class = "V10CredentialExchangeSchema"

    RECORD_TYPE = "v10_credential_exchange"
    RECORD_ID_NAME = "credential_exchange_id"
    WEBHOOK_TOPIC = "Aries#0036 v1.0 credentials"

    INITIATOR_SELF = "self"
    INITIATOR_EXTERNAL = "external"

    STATE_PROPOSAL_SENT = "proposal_sent"
    STATE_PROPOSAL_RECEIVED = "proposal_received"
    STATE_OFFER_SENT = "offer_sent"
    STATE_OFFER_RECEIVED = "offer_received"
    STATE_REQUEST_SENT = "request_sent"
    STATE_REQUEST_RECEIVED = "request_received"
    STATE_ISSUED = "issued"
    STATE_STORED = "stored"

    def __init__(
        self,
        *,
        credential_exchange_id: str = None,
        connection_id: str = None,
        thread_id: str = None,
        parent_thread_id: str = None,
        initiator: str = None,
        state: str = None,
        credential_definition_id: str = None,
        schema_id: str = None,
        credential_proposal_dict: dict = None,  # serialized credential proposal message
        credential_offer: dict = None,  # indy credential offer
        credential_request: dict = None,  # indy credential request
        credential_request_metadata: dict = None,
        credential_id: str = None,
        credential: dict = None,  # indy credential
        auto_offer: bool = False,
        auto_issue: bool = False,
        error_msg: str = None,
        **kwargs
    ):
        """Initialize a new V10CredentialExchange."""
        super().__init__(credential_exchange_id, state, **kwargs)
        self._id = credential_exchange_id
        self.connection_id = connection_id
        self.thread_id = thread_id
        self.parent_thread_id = parent_thread_id
        self.initiator = initiator
        self.state = state
        self.credential_definition_id = credential_definition_id
        self.schema_id = schema_id
        self.credential_proposal_dict = credential_proposal_dict
        self.credential_offer = credential_offer
        self.credential_request = credential_request
        self.credential_request_metadata = credential_request_metadata
        self.credential_id = credential_id
        self.credential = credential
        self.auto_offer = auto_offer
        self.auto_issue = auto_issue
        self.error_msg = error_msg

    @property
    def credential_exchange_id(self) -> str:
        """Accessor for the ID associated with this exchange."""
        return self._id

    @property
    def record_value(self) -> dict:
        """Accessor for the JSON record value generated for this credential exchange."""
        result = self.tags
        for prop in (
            "credential_proposal_dict",
            "credential_offer",
            "credential_request",
            "credential_request_metadata",
            "error_msg",
            "auto_offer",
            "auto_issue",
            "credential",
            "parent_thread_id"
        ):
            val = getattr(self, prop)
            if val:
                result[prop] = val
        return result

    @property
    def record_tags(self) -> dict:
        """Accessor for the record tags generated for this credential exchange."""
        result = {}
        for prop in (
            "connection_id",
            "thread_id",
            "initiator",
            "state",
            "credential_definition_id",
            "schema_id",
            "credential_id",
        ):
            val = getattr(self, prop)
            if val:
                result[prop] = val
        return result


class V10CredentialExchangeSchema(BaseRecordSchema):
    """Schema to allow serialization/deserialization of credential exchange records."""

    class Meta:
        """V10CredentialExchangeSchema metadata."""

        model_class = V10CredentialExchange

    credential_exchange_id = fields.Str(required=False)
    connection_id = fields.Str(required=False)
    thread_id = fields.Str(required=False)
    parent_thread_id = fields.Str(required=False)
    initiator = fields.Str(required=False)
    state = fields.Str(required=False)
    credential_definition_id = fields.Str(required=False)
    schema_id = fields.Str(required=False)
    credential_proposal_dict = fields.Dict(required=False)
    credential_offer = fields.Dict(required=False)
    credential_request = fields.Dict(required=False)
    credential_request_metadata = fields.Dict(required=False)
    credential_id = fields.Str(required=False)
    credential = fields.Dict(required=False)
    auto_offer = fields.Bool(required=False)
    auto_issue = fields.Bool(required=False)
    error_msg = fields.Str(required=False)
