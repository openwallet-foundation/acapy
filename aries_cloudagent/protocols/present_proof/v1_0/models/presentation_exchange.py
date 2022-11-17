"""Aries#0037 v1.0 presentation exchange information with non-secrets storage."""

import logging

from typing import Any, Mapping, Optional, Union

from marshmallow import fields, validate

from .....core.profile import ProfileSession
from .....indy.models.proof import IndyProof, IndyProofSchema
from .....indy.models.proof_request import IndyProofRequest, IndyProofRequestSchema
from .....messaging.models.base_record import BaseExchangeRecord, BaseExchangeSchema
from .....messaging.valid import UUIDFour
from .....storage.base import StorageError

from ..messages.presentation_proposal import (
    PresentationProposal,
    PresentationProposalSchema,
)
from ..messages.presentation_request import (
    PresentationRequest,
    PresentationRequestSchema,
)

from . import UNENCRYPTED_TAGS

LOGGER = logging.getLogger(__name__)


class V10PresentationExchange(BaseExchangeRecord):
    """Represents an Aries#0037 v1.0 presentation exchange."""

    class Meta:
        """V10PresentationExchange metadata."""

        schema_class = "V10PresentationExchangeSchema"

    RECORD_TYPE = "presentation_exchange_v10"
    RECORD_ID_NAME = "presentation_exchange_id"
    RECORD_TOPIC = "present_proof"
    TAG_NAMES = {"~thread_id"} if UNENCRYPTED_TAGS else {"thread_id"}

    INITIATOR_SELF = "self"
    INITIATOR_EXTERNAL = "external"

    ROLE_PROVER = "prover"
    ROLE_VERIFIER = "verifier"

    STATE_PROPOSAL_SENT = "proposal_sent"
    STATE_PROPOSAL_RECEIVED = "proposal_received"
    STATE_REQUEST_SENT = "request_sent"
    STATE_REQUEST_RECEIVED = "request_received"
    STATE_PRESENTATION_SENT = "presentation_sent"
    STATE_PRESENTATION_RECEIVED = "presentation_received"
    STATE_VERIFIED = "verified"
    STATE_PRESENTATION_ACKED = "presentation_acked"
    STATE_ABANDONED = "abandoned"

    def __init__(
        self,
        *,
        presentation_exchange_id: str = None,
        connection_id: Optional[str] = None,
        thread_id: str = None,
        initiator: str = None,
        role: str = None,
        state: str = None,
        presentation_proposal_dict: Union[
            PresentationProposal, Mapping
        ] = None,  # aries message: ..._dict for historic compat on all aries msgs
        presentation_request: Union[IndyProofRequest, Mapping] = None,  # indy proof req
        presentation_request_dict: Union[
            PresentationRequest, Mapping
        ] = None,  # aries message
        presentation: Union[IndyProof, Mapping] = None,  # indy proof
        verified: str = None,
        verified_msgs: list = None,
        auto_present: bool = False,
        auto_verify: bool = False,
        error_msg: str = None,
        trace: bool = False,  # backward compat: BaseRecord.from_storage()
        **kwargs,
    ):
        """Initialize a new PresentationExchange."""
        super().__init__(presentation_exchange_id, state, trace=trace, **kwargs)
        self.connection_id = connection_id
        self.thread_id = thread_id
        self.initiator = initiator
        self.role = role
        self.state = state
        self._presentation_proposal_dict = PresentationProposal.serde(
            presentation_proposal_dict
        )
        self._presentation_request = IndyProofRequest.serde(presentation_request)
        self._presentation_request_dict = PresentationRequest.serde(
            presentation_request_dict
        )
        self._presentation = IndyProof.serde(presentation)
        self.verified = verified
        self.verified_msgs = verified_msgs
        self.auto_present = auto_present
        self.auto_verify = auto_verify
        self.error_msg = error_msg

    @property
    def presentation_exchange_id(self) -> str:
        """Accessor for the ID associated with this exchange."""
        return self._id

    @property
    def presentation_proposal_dict(self) -> PresentationProposal:
        """Accessor; get deserialized view."""
        return (
            None
            if self._presentation_proposal_dict is None
            else self._presentation_proposal_dict.de
        )

    @presentation_proposal_dict.setter
    def presentation_proposal_dict(self, value):
        """Setter; store de/serialized views."""
        self._presentation_proposal_dict = PresentationProposal.serde(value)

    @property
    def presentation_request(self) -> IndyProofRequest:
        """Accessor; get deserialized view."""
        return (
            None
            if self._presentation_request is None
            else self._presentation_request.de
        )

    @presentation_request.setter
    def presentation_request(self, value):
        """Setter; store de/serialized views."""
        self._presentation_request = IndyProofRequest.serde(value)

    @property
    def presentation_request_dict(self) -> PresentationRequest:
        """Accessor; get deserialized view."""
        return (
            None
            if self._presentation_request_dict is None
            else self._presentation_request_dict.de
        )

    @presentation_request_dict.setter
    def presentation_request_dict(self, value):
        """Setter; store de/serialized views."""
        self._presentation_request_dict = PresentationRequest.serde(value)

    @property
    def presentation(self) -> IndyProof:
        """Accessor; get deserialized view."""
        return None if self._presentation is None else self._presentation.de

    @presentation.setter
    def presentation(self, value):
        """Setter; store de/serialized views."""
        self._presentation = IndyProof.serde(value)

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

        self.state = state or V10PresentationExchange.STATE_ABANDONED
        if reason:
            self.error_msg = reason

        try:
            await self.save(
                session,
                reason=reason,
                log_params=log_params,
                log_override=log_override,
            )
        except StorageError as err:
            LOGGER.exception(err)

    @property
    def record_value(self) -> Mapping:
        """Accessor for the JSON record value generated for this credential exchange."""
        retval = {
            **{
                prop: getattr(self, prop)
                for prop in (
                    "connection_id",
                    "initiator",
                    "role",
                    "state",
                    "auto_present",
                    "auto_verify",
                    "error_msg",
                    "verified",
                    "verified_msgs",
                    "trace",
                )
            },
            **{
                prop: getattr(self, f"_{prop}").ser
                for prop in (
                    "presentation_proposal_dict",
                    "presentation_request",
                    "presentation_request_dict",
                    "presentation",
                )
                if getattr(self, prop) is not None
            },
        }
        return retval

    def __eq__(self, other: Any) -> bool:
        """Comparison between records."""
        return super().__eq__(other)


class V10PresentationExchangeSchema(BaseExchangeSchema):
    """Schema for de/serialization of v1.0 presentation exchange records."""

    class Meta:
        """V10PresentationExchangeSchema metadata."""

        model_class = V10PresentationExchange

    presentation_exchange_id = fields.Str(
        required=False,
        description="Presentation exchange identifier",
        example=UUIDFour.EXAMPLE,  # typically a UUID4 but not necessarily
    )
    connection_id = fields.Str(
        required=False,
        description="Connection identifier",
        example=UUIDFour.EXAMPLE,  # typically a UUID4 but not necessarily
    )
    thread_id = fields.Str(
        required=False,
        description="Thread identifier",
        example=UUIDFour.EXAMPLE,  # typically a UUID4 but not necessarily
    )
    initiator = fields.Str(
        required=False,
        description="Present-proof exchange initiator: self or external",
        example=V10PresentationExchange.INITIATOR_SELF,
        validate=validate.OneOf(["self", "external"]),
    )
    role = fields.Str(
        required=False,
        description="Present-proof exchange role: prover or verifier",
        example=V10PresentationExchange.ROLE_PROVER,
        validate=validate.OneOf(["prover", "verifier"]),
    )
    state = fields.Str(
        required=False,
        description="Present-proof exchange state",
        example=V10PresentationExchange.STATE_VERIFIED,
    )
    presentation_proposal_dict = fields.Nested(
        PresentationProposalSchema(),
        required=False,
        description="Presentation proposal message",
    )
    presentation_request = fields.Nested(
        IndyProofRequestSchema(),
        required=False,
        description="(Indy) presentation request (also known as proof request)",
    )
    presentation_request_dict = fields.Nested(
        PresentationRequestSchema(),
        required=False,
        description="Presentation request message",
    )
    presentation = fields.Nested(
        IndyProofSchema(),
        required=False,
        description="(Indy) presentation (also known as proof)",
    )
    verified = fields.Str(  # tag: must be a string
        required=False,
        description="Whether presentation is verified: true or false",
        example="true",
        validate=validate.OneOf(["true", "false"]),
    )
    verified_msgs = fields.List(
        fields.Str(
            required=False,
            description="Proof verification warning or error information",
        ),
        required=False,
    )
    auto_present = fields.Bool(
        required=False,
        description="Prover choice to auto-present proof as verifier requests",
        example=False,
    )
    auto_verify = fields.Bool(
        required=False, description="Verifier choice to auto-verify proof presentation"
    )
    error_msg = fields.Str(
        required=False, description="Error message", example="Invalid structure"
    )
