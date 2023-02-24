"""Aries#0036 v1.0 credential exchange information with non-secrets storage."""

import logging

from typing import Any, Mapping, Optional, Union

from marshmallow import fields, validate

from .....core.profile import ProfileSession
from .....indy.models.cred import IndyCredential, IndyCredentialSchema
from .....indy.models.cred_abstract import IndyCredAbstract, IndyCredAbstractSchema
from .....indy.models.cred_precis import IndyCredInfo, IndyCredInfoSchema
from .....indy.models.cred_request import IndyCredRequest, IndyCredRequestSchema
from .....messaging.models.base_record import BaseExchangeRecord, BaseExchangeSchema
from .....messaging.valid import INDY_CRED_DEF_ID, INDY_SCHEMA_ID, UUIDFour
from .....storage.base import StorageError

from ..messages.credential_proposal import CredentialProposal, CredentialProposalSchema
from ..messages.credential_offer import CredentialOffer, CredentialOfferSchema
from ..messages.credential_exchange_webhook import (
    V10CredentialExchangeWebhook,
)

from . import UNENCRYPTED_TAGS

LOGGER = logging.getLogger(__name__)


class V10CredentialExchange(BaseExchangeRecord):
    """Represents an Aries#0036 credential exchange."""

    class Meta:
        """CredentialExchange metadata."""

        schema_class = "V10CredentialExchangeSchema"

    RECORD_TYPE = "credential_exchange_v10"
    RECORD_ID_NAME = "credential_exchange_id"
    RECORD_TOPIC = "issue_credential"
    TAG_NAMES = {"~thread_id"} if UNENCRYPTED_TAGS else {"thread_id"}

    INITIATOR_SELF = "self"
    INITIATOR_EXTERNAL = "external"
    ROLE_ISSUER = "issuer"
    ROLE_HOLDER = "holder"

    STATE_PROPOSAL_SENT = "proposal_sent"
    STATE_PROPOSAL_RECEIVED = "proposal_received"
    STATE_OFFER_SENT = "offer_sent"
    STATE_OFFER_RECEIVED = "offer_received"
    STATE_REQUEST_SENT = "request_sent"
    STATE_REQUEST_RECEIVED = "request_received"
    STATE_ISSUED = "credential_issued"
    STATE_CREDENTIAL_RECEIVED = "credential_received"
    STATE_ACKED = "credential_acked"
    STATE_CREDENTIAL_REVOKED = "credential_revoked"
    STATE_ABANDONED = "abandoned"

    def __init__(
        self,
        *,
        credential_exchange_id: str = None,
        connection_id: Optional[str] = None,
        thread_id: str = None,
        parent_thread_id: str = None,
        initiator: str = None,
        role: str = None,
        state: str = None,
        credential_definition_id: str = None,
        schema_id: str = None,
        credential_proposal_dict: Union[
            Mapping, CredentialProposal
        ] = None,  # aries message: ..._dict for historic compat on all aries msgs
        credential_offer_dict: Union[Mapping, CredentialOffer] = None,  # aries message
        credential_offer: Union[Mapping, IndyCredAbstract] = None,  # indy artifact
        credential_request: Union[Mapping, IndyCredRequest] = None,  # indy artifact
        credential_request_metadata: Mapping = None,
        credential_id: str = None,
        raw_credential: Union[Mapping, IndyCredential] = None,  # indy cred as received
        credential: Union[Mapping, IndyCredInfo] = None,  # indy cred as stored
        revoc_reg_id: str = None,
        revocation_id: str = None,
        auto_offer: bool = False,
        auto_issue: bool = False,
        auto_remove: bool = True,
        error_msg: str = None,
        trace: bool = False,  # backward-compat: BaseRecord.from_storage()
        **kwargs,
    ):
        """Initialize a new V10CredentialExchange."""
        super().__init__(credential_exchange_id, state, trace=trace, **kwargs)
        self._id = credential_exchange_id
        self.connection_id = connection_id
        self.thread_id = thread_id
        self.parent_thread_id = parent_thread_id
        self.initiator = initiator
        self.role = role
        self.state = state
        self.credential_definition_id = credential_definition_id
        self.schema_id = schema_id
        self._credential_proposal_dict = CredentialProposal.serde(
            credential_proposal_dict
        )
        self._credential_offer_dict = CredentialOffer.serde(credential_offer_dict)
        self._credential_offer = IndyCredAbstract.serde(credential_offer)
        self._credential_request = IndyCredRequest.serde(credential_request)
        self.credential_request_metadata = credential_request_metadata
        self.credential_id = credential_id
        self._raw_credential = IndyCredential.serde(raw_credential)
        self._credential = IndyCredInfo.serde(credential)
        self.revoc_reg_id = revoc_reg_id
        self.revocation_id = revocation_id
        self.auto_offer = auto_offer
        self.auto_issue = auto_issue
        self.auto_remove = auto_remove
        self.error_msg = error_msg

    @property
    def credential_exchange_id(self) -> str:
        """Accessor for the ID associated with this exchange."""
        return self._id

    @property
    def credential_proposal_dict(self) -> CredentialProposal:
        """Accessor; get deserialized view."""
        return (
            None
            if self._credential_proposal_dict is None
            else self._credential_proposal_dict.de
        )

    @credential_proposal_dict.setter
    def credential_proposal_dict(self, value):
        """Setter; store de/serialized views."""
        self._credential_proposal_dict = CredentialProposal.serde(value)

    @property
    def credential_offer_dict(self) -> CredentialOffer:
        """Accessor; get deserialized view."""
        return (
            None
            if self._credential_offer_dict is None
            else self._credential_offer_dict.de
        )

    @credential_offer_dict.setter
    def credential_offer_dict(self, value):
        """Setter; store de/serialized views."""
        self._credential_offer_dict = CredentialOffer.serde(value)

    @property
    def credential_offer(self) -> IndyCredAbstract:
        """Accessor; get deserialized view."""
        return None if self._credential_offer is None else self._credential_offer.de

    @credential_offer.setter
    def credential_offer(self, value):
        """Setter; store de/serialized views."""
        self._credential_offer = IndyCredAbstract.serde(value)

    @property
    def credential_request(self) -> IndyCredRequest:
        """Accessor; get deserialized view."""
        return None if self._credential_request is None else self._credential_request.de

    @credential_request.setter
    def credential_request(self, value):
        """Setter; store de/serialized views."""
        self._credential_request = IndyCredRequest.serde(value)

    @property
    def raw_credential(self) -> IndyCredential:
        """Accessor; get deserialized view."""
        return None if self._raw_credential is None else self._raw_credential.de

    @raw_credential.setter
    def raw_credential(self, value):
        """Setter; store de/serialized views."""
        self._raw_credential = IndyCredential.serde(value)

    @property
    def credential(self) -> IndyCredInfo:
        """Accessor; get deserialized view."""
        return None if self._credential is None else self._credential.de

    @credential.setter
    def credential(self, value):
        """Setter; store de/serialized views."""
        self._credential = IndyCredInfo.serde(value)

    async def save_error_state(
        self,
        session: ProfileSession,
        *,
        state: str = None,
        reason: str = None,
        log_params: Mapping[str, Any] = None,
        log_override: bool = False,
    ):
        """
        Save record error state if need be; log and swallow any storage error.

        Args:
            session: The profile session to use
            reason: A reason to add to the log
            log_params: Additional parameters to log
            override: Override configured logging regimen, print to stderr instead
        """

        if self._last_state == state:  # already done
            return

        self.state = state or V10CredentialExchange.STATE_ABANDONED
        if reason:
            self.error_msg = reason

        try:
            await self.save(
                session,
                reason=reason,
                log_params=log_params,
                log_override=log_override,
            )
        except StorageError:
            LOGGER.exception("Error saving credential exchange error state")

    # Override
    async def emit_event(self, session: ProfileSession, payload: Any = None):
        """
        Emit an event.

        Args:
            session: The profile session to use
            payload: The event payload
        """

        if not self.RECORD_TOPIC:
            return

        if self.state:
            topic = f"{self.EVENT_NAMESPACE}::{self.RECORD_TOPIC}::{self.state}"
        else:
            topic = f"{self.EVENT_NAMESPACE}::{self.RECORD_TOPIC}"

        if session.profile.settings.get("debug.webhooks"):
            if not payload:
                payload = self.serialize()
        else:
            payload = V10CredentialExchangeWebhook(**self.__dict__)
            payload = payload.__dict__

        await session.profile.notify(topic, payload)

    @property
    def record_value(self) -> dict:
        """Accessor for the JSON record value generated for this invitation."""
        return {
            **{
                prop: getattr(self, prop)
                for prop in (
                    "connection_id",
                    "credential_request_metadata",
                    "error_msg",
                    "auto_offer",
                    "auto_issue",
                    "auto_remove",
                    "parent_thread_id",
                    "initiator",
                    "credential_definition_id",
                    "schema_id",
                    "credential_id",
                    "revoc_reg_id",
                    "revocation_id",
                    "role",
                    "state",
                    "trace",
                )
            },
            **{
                prop: getattr(self, f"_{prop}").ser
                for prop in (
                    "credential_proposal_dict",
                    "credential_offer_dict",
                    "credential_offer",
                    "credential_request",
                    "raw_credential",
                    "credential",
                )
                if getattr(self, prop) is not None
            },
        }

    @classmethod
    async def retrieve_by_connection_and_thread(
        cls,
        session: ProfileSession,
        connection_id: Optional[str],
        thread_id: str,
        role: Optional[str] = None,
        *,
        for_update=False,
    ) -> "V10CredentialExchange":
        """Retrieve a credential exchange record by connection and thread ID."""
        cache_key = f"credential_exchange_ctidx::{connection_id}::{thread_id}::{role}"
        record_id = await cls.get_cached_key(session, cache_key)
        if record_id:
            record = await cls.retrieve_by_id(session, record_id, for_update=for_update)
        else:
            post_filter = {}
            if role:
                post_filter["role"] = role
            if connection_id:
                post_filter["connection_id"] = connection_id
            record = await cls.retrieve_by_tag_filter(
                session,
                {"thread_id": thread_id},
                post_filter,
                for_update=for_update,
            )
            await cls.set_cached_key(session, cache_key, record.credential_exchange_id)
        return record

    def __eq__(self, other: Any) -> bool:
        """Comparison between records."""
        return super().__eq__(other)


class V10CredentialExchangeSchema(BaseExchangeSchema):
    """Schema to allow serialization/deserialization of credential exchange records."""

    class Meta:
        """V10CredentialExchangeSchema metadata."""

        model_class = V10CredentialExchange

    credential_exchange_id = fields.Str(
        required=False,
        description="Credential exchange identifier",
        example=UUIDFour.EXAMPLE,
    )
    connection_id = fields.Str(
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
        example=V10CredentialExchange.INITIATOR_SELF,
        validate=validate.OneOf(["self", "external"]),
    )
    role = fields.Str(
        required=False,
        description="Issue-credential exchange role: holder or issuer",
        example=V10CredentialExchange.ROLE_ISSUER,
        validate=validate.OneOf(["holder", "issuer"]),
    )
    state = fields.Str(
        required=False,
        description="Issue-credential exchange state",
        example=V10CredentialExchange.STATE_ACKED,
    )
    credential_definition_id = fields.Str(
        required=False,
        description="Credential definition identifier",
        **INDY_CRED_DEF_ID,
    )
    schema_id = fields.Str(
        required=False, description="Schema identifier", **INDY_SCHEMA_ID
    )
    credential_proposal_dict = fields.Nested(
        CredentialProposalSchema(),
        required=False,
        description="Credential proposal message",
    )
    credential_offer_dict = fields.Nested(
        CredentialOfferSchema(),
        required=False,
        description="Credential offer message",
    )
    credential_offer = fields.Nested(
        IndyCredAbstractSchema(),
        required=False,
        description="(Indy) credential offer",
    )
    credential_request = fields.Nested(
        IndyCredRequestSchema(),
        required=False,
        description="(Indy) credential request",
    )
    credential_request_metadata = fields.Dict(
        required=False, description="(Indy) credential request metadata"
    )
    credential_id = fields.Str(
        required=False, description="Credential identifier", example=UUIDFour.EXAMPLE
    )
    raw_credential = fields.Nested(
        IndyCredentialSchema(),
        required=False,
        description="Credential as received, prior to storage in holder wallet",
    )
    credential = fields.Nested(
        IndyCredInfoSchema(),
        required=False,
        description="Credential as stored",
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
        example="Credential definition identifier is not set in proposal",
    )
    revoc_reg_id = fields.Str(
        required=False, description="Revocation registry identifier"
    )
    revocation_id = fields.Str(
        required=False, description="Credential identifier within revocation registry"
    )
