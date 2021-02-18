"""Aries#0036 v1.0 credential exchange information with non-secrets storage."""

from typing import Any, Mapping

from marshmallow import fields, validate

from .....core.profile import ProfileSession
from .....messaging.models.base_record import BaseExchangeRecord, BaseExchangeSchema
from .....messaging.valid import UUIDFour

from . import UNENCRYPTED_TAGS


class V20CredExRecord(BaseExchangeRecord):
    """Represents an Aries#0036 credential exchange."""

    class Meta:
        """CredentialExchange metadata."""

        schema_class = "V20CredExRecordSchema"

    RECORD_TYPE = "cred_ex_v20"
    RECORD_ID_NAME = "cred_ex_id"
    WEBHOOK_TOPIC = "issue_credential_v2_0"
    TAG_NAMES = {"~thread_id"} if UNENCRYPTED_TAGS else {"thread_id"}

    INITIATOR_SELF = "self"
    INITIATOR_EXTERNAL = "external"
    ROLE_ISSUER = "issuer"
    ROLE_HOLDER = "holder"

    STATE_PROPOSAL_SENT = "proposal-sent"
    STATE_PROPOSAL_RECEIVED = "proposal-received"
    STATE_OFFER_SENT = "offer-sent"
    STATE_OFFER_RECEIVED = "offer-received"
    STATE_REQUEST_SENT = "request-sent"
    STATE_REQUEST_RECEIVED = "request-received"
    STATE_ISSUED = "credential-issued"
    STATE_CREDENTIAL_RECEIVED = "credential-received"
    STATE_DONE = "done"

    def __init__(
        self,
        *,
        cred_ex_id: str = None,
        conn_id: str = None,
        thread_id: str = None,
        parent_thread_id: str = None,
        initiator: str = None,
        role: str = None,
        state: str = None,
        cred_proposal: Mapping = None,  # serialized cred proposal message
        cred_offer: Mapping = None,  # serialized cred offer message
        cred_request: Mapping = None,  # serialized cred request message
        cred_request_metadata: Mapping = None,  # credential request metadata
        cred_issue: Mapping = None,  # serialized cred issue message
        cred_id_stored: str = None,
        auto_offer: bool = False,
        auto_issue: bool = False,
        auto_remove: bool = True,
        error_msg: str = None,
        trace: bool = False,
        **kwargs,
    ):
        """Initialize a new V20CredExRecord."""
        super().__init__(cred_ex_id, state, trace=trace, **kwargs)
        self._id = cred_ex_id
        self.conn_id = conn_id
        self.thread_id = thread_id
        self.parent_thread_id = parent_thread_id
        self.initiator = initiator
        self.role = role
        self.state = state
        self.cred_proposal = cred_proposal
        self.cred_offer = cred_offer
        self.cred_request = cred_request
        self.cred_request_metadata = cred_request_metadata
        self.cred_issue = cred_issue
        self.cred_id_stored = cred_id_stored
        self.auto_offer = auto_offer
        self.auto_issue = auto_issue
        self.auto_remove = auto_remove
        self.error_msg = error_msg
        self.trace = trace

    @property
    def cred_ex_id(self) -> str:
        """Accessor for the ID associated with this exchange."""
        return self._id

    @property
    def connection_id(self) -> str:
        """Synonym for conn_id."""
        return self.conn_id

    @property
    def cred_preview(self) -> Mapping:
        """Credential preview from credential proposal."""
        return (
            self.cred_proposal and self.cred_proposal.get("credential_preview") or None
        )

    @property
    def record_value(self) -> Mapping:
        """Accessor for the JSON record value generated for this credential exchange."""
        return {
            prop: getattr(self, prop)
            for prop in (
                "conn_id",
                "parent_thread_id",
                "initiator",
                "role",
                "state",
                "cred_proposal",
                "cred_offer",
                "cred_request",
                "cred_request_metadata",
                "cred_issue",
                "cred_id_stored",
                "auto_offer",
                "auto_issue",
                "auto_remove",
                "error_msg",
                "trace",
            )
        }

    @classmethod
    async def retrieve_by_conn_and_thread(
        cls, session: ProfileSession, conn_id: str, thread_id: str
    ) -> "V20CredExRecord":
        """Retrieve a credential exchange record by connection and thread ID."""
        cache_key = f"credential_exchange_ctidx::{conn_id}::{thread_id}"
        record_id = await cls.get_cached_key(session, cache_key)
        if record_id:
            record = await cls.retrieve_by_id(session, record_id)
        else:
            record = await cls.retrieve_by_tag_filter(
                session,
                {"thread_id": thread_id},
                {"conn_id": conn_id} if conn_id else None,
            )
            await cls.set_cached_key(session, cache_key, record.cred_ex_id)
        return record

    def __eq__(self, other: Any) -> bool:
        """Comparison between records."""
        return super().__eq__(other)


class V20CredExRecordSchema(BaseExchangeSchema):
    """Schema to allow serialization/deserialization of credential exchange records."""

    class Meta:
        """V20CredExSchema metadata."""

        model_class = V20CredExRecord

    cred_ex_id = fields.Str(
        required=False,
        description="Credential exchange identifier",
        example=UUIDFour.EXAMPLE,
    )
    conn_id = fields.Str(
        required=False, description="Connection identifier", example=UUIDFour.EXAMPLE
    )
    thread_id = fields.Str(
        required=False, description="Thread identifier", example=UUIDFour.EXAMPLE
    )
    parent_thread_id = fields.Str(
        required=False, description="Parent thread identifier", example=UUIDFour.EXAMPLE
    )
    initiator = fields.Str(
        required=False,
        description="Issue-credential exchange initiator: self or external",
        example=V20CredExRecord.INITIATOR_SELF,
        validate=validate.OneOf(
            [
                getattr(V20CredExRecord, m)
                for m in vars(V20CredExRecord)
                if m.startswith("INITIATOR_")
            ]
        ),
    )
    role = fields.Str(
        required=False,
        description="Issue-credential exchange role: holder or issuer",
        example=V20CredExRecord.ROLE_ISSUER,
        validate=validate.OneOf(
            [
                getattr(V20CredExRecord, m)
                for m in vars(V20CredExRecord)
                if m.startswith("ROLE_")
            ]
        ),
    )
    state = fields.Str(
        required=False,
        description="Issue-credential exchange state",
        example=V20CredExRecord.STATE_DONE,
        validate=validate.OneOf(
            [
                getattr(V20CredExRecord, m)
                for m in vars(V20CredExRecord)
                if m.startswith("STATE_")
            ]
        ),
    )
    cred_preview = fields.Dict(
        required=False,
        dump_only=True,
        description="Serialized credential preview from credential proposal",
    )
    cred_proposal = fields.Dict(
        required=False, description="Serialized credential proposal message"
    )
    cred_offer = fields.Dict(
        required=False, description="Serialized credential offer message"
    )
    cred_request = fields.Dict(
        required=False, description="Serialized credential request message"
    )
    cred_request_metadata = fields.Dict(
        required=False, description="(Indy) credential request metadata"
    )
    cred_issue = fields.Dict(
        required=False, description="Serialized credential issue message"
    )
    auto_offer = fields.Bool(
        required=False,
        description="Holder choice to accept offer in this credential exchange",
        example=False,
    )
    auto_issue = fields.Bool(
        required=False,
        description="Issuer choice to issue to request in this credential exchange",
        example=False,
    )
    auto_remove = fields.Bool(
        required=False,
        default=True,
        description=(
            "Issuer choice to remove this credential exchange record when complete"
        ),
        example=False,
    )
    error_msg = fields.Str(
        required=False,
        description="Error message",
        example="The front fell off",
    )
    cred_id_stored = fields.Str(
        required=False,
        description="Credential identifier stored in wallet",
        example=UUIDFour.EXAMPLE,
    )
