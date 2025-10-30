"""Events fired by AnonCreds interface."""

from typing import NamedTuple, Optional, Protocol

from ..core.event_bus import Event
from .models.revocation import RevListResult, RevRegDef, RevRegDefResult

FIRST_REGISTRY_TAG = str(0)  # This tag is used to signify it is the first registry


# Initial credential definition event, kicks off the revocation setup process
CRED_DEF_FINISHED_EVENT = "anoncreds::credential-definition::finished"

# Revocation registry definition events
REV_REG_DEF_CREATE_REQUESTED_EVENT = (
    "anoncreds::revocation-registry-definition::create-requested"
)
# Response triggers the "store" event
REV_REG_DEF_CREATE_RESPONSE_EVENT = (
    "anoncreds::revocation-registry-definition::create-response"
)

# Store the rev reg result events
REV_REG_DEF_STORE_REQUESTED_EVENT = (
    "anoncreds::revocation-registry-definition::store-requested"
)
# Response triggers the "Finished" event, as well as backup creation, if first registry
REV_REG_DEF_STORE_RESPONSE_EVENT = (
    "anoncreds::revocation-registry-definition::store-response"
)

# The above successful storage of rev reg def event, triggers create rev list event
# TODO: superfluous event, can be merged with above rev-reg-def-store response
# Just exists for backwards compatibility with old code
REV_REG_DEF_FINISHED_EVENT = "anoncreds::revocation-registry-definition::finished"

# Revocation list events
REV_LIST_CREATE_REQUESTED_EVENT = "anoncreds::revocation-list::create-requested"
REV_LIST_CREATE_RESPONSE_EVENT = "anoncreds::revocation-list::create-response"

# The above rev-list-create-response triggers the rev-list store event:
REV_LIST_STORE_REQUESTED_EVENT = "anoncreds::revocation-list::store-requested"
# Store response triggers the activation event, if it's for the first registry
REV_LIST_STORE_RESPONSE_EVENT = "anoncreds::revocation-list::store-response"

# TODO: Just exists for backwards compatibility with old code. Not used in state machine
REV_LIST_FINISHED_EVENT = "anoncreds::revocation-list::finished"

# Rev reg activation events. Triggered for first registry, and then during full handling
REV_REG_ACTIVATION_REQUESTED_EVENT = (
    "anoncreds::revocation-registry::activation-requested"
)
REV_REG_ACTIVATION_RESPONSE_EVENT = "anoncreds::revocation-registry::activation-response"

# Revocation registry full events:
# - Sets current registry to full,
# - Emits event to activate backup,
# - And emits event to create new backup
REV_REG_FULL_DETECTED_EVENT = "anoncreds::revocation-registry::full-detected"
# Full handling completed is emitted after current registry is set to full -
# (not after backup is activated or new one is created, those are queued asynchronously)
REV_REG_FULL_HANDLING_COMPLETED_EVENT = (
    "anoncreds::revocation-registry::full-handling-completed"
)

# If retries continue to fail, this will notify the issuer that intervention is required
INTERVENTION_REQUIRED_EVENT = "anoncreds::revocation-registry::intervention-required"


class BaseEventPayload(Protocol):
    """Base event payload."""

    options: dict


class BasePayloadWithFailure(Protocol):
    """Base payload with failure."""

    failure: "BaseFailurePayload"
    options: dict


class BaseFailurePayload(Protocol):
    """Base failure payload."""

    error_info: "ErrorInfoPayload"


class ErrorInfoPayload(NamedTuple):
    """Common error information for all response events."""

    error_msg: str
    should_retry: bool
    retry_count: int


class CredDefFinishedPayload(NamedTuple):
    """Payload of cred def finished event."""

    schema_id: str
    cred_def_id: str
    issuer_id: str
    support_revocation: bool
    max_cred_num: int
    options: dict


class CredDefFinishedEvent(Event):
    """Event for cred def finished."""

    event_topic = CRED_DEF_FINISHED_EVENT

    def __init__(
        self,
        payload: CredDefFinishedPayload,
    ):
        """Initialize an instance.

        Args:
            payload: CredDefFinishedPayload

        """
        self._topic = self.event_topic
        self._payload = payload

    @classmethod
    def with_payload(
        cls,
        schema_id: str,
        cred_def_id: str,
        issuer_id: str,
        support_revocation: bool,
        max_cred_num: int,
        options: Optional[dict] = None,
    ):
        """With payload."""
        payload = CredDefFinishedPayload(
            schema_id=schema_id,
            cred_def_id=cred_def_id,
            issuer_id=issuer_id,
            support_revocation=support_revocation,
            max_cred_num=max_cred_num,
            options=options or {},
        )
        return cls(payload)

    @property
    def payload(self) -> CredDefFinishedPayload:
        """Return payload."""
        return self._payload


class RevRegDefFinishedPayload(NamedTuple):
    """Payload of rev reg def finished event."""

    rev_reg_def_id: str
    rev_reg_def: RevRegDef
    options: dict


class RevRegDefFinishedEvent(Event):
    """Event for rev reg def finished."""

    event_topic = REV_REG_DEF_FINISHED_EVENT

    def __init__(self, payload: RevRegDefFinishedPayload):
        """Initialize an instance.

        Args:
            payload: RevRegDefFinishedPayload

        """
        self._topic = self.event_topic
        self._payload = payload

    @classmethod
    def with_payload(
        cls,
        *,
        rev_reg_def_id: str,
        rev_reg_def: RevRegDef,
        options: Optional[dict] = None,
    ):
        """With payload."""
        payload = RevRegDefFinishedPayload(
            rev_reg_def_id=rev_reg_def_id,
            rev_reg_def=rev_reg_def,
            options=options or {},
        )
        return cls(payload)

    @property
    def payload(self) -> RevRegDefFinishedPayload:
        """Return payload."""
        return self._payload


class RevListFinishedPayload(NamedTuple):
    """Payload of rev list finished event."""

    rev_reg_id: str
    revoked: list
    options: dict


class RevListFinishedEvent(Event):
    """Event for rev list finished."""

    event_topic = REV_LIST_FINISHED_EVENT

    def __init__(self, payload: RevListFinishedPayload):
        """Initialize an instance.

        Args:
            payload: RevListFinishedPayload

        """
        self._topic = self.event_topic
        self._payload = payload

    @classmethod
    def with_payload(
        cls,
        rev_reg_id: str,
        revoked: list,
        options: Optional[dict] = None,
    ):
        """With payload."""
        payload = RevListFinishedPayload(
            rev_reg_id=rev_reg_id,
            revoked=revoked,
            options=options or {},
        )
        return cls(payload)

    @property
    def payload(self) -> RevListFinishedPayload:
        """Return payload."""
        return self._payload


class RevRegDefCreateRequestedPayload(NamedTuple):
    """Payload for rev reg def create requested event."""

    issuer_id: str
    cred_def_id: str
    registry_type: str
    tag: str
    max_cred_num: int
    options: dict


class RevRegDefCreateRequestedEvent(Event):
    """Event for rev reg def create requested."""

    event_topic = REV_REG_DEF_CREATE_REQUESTED_EVENT

    def __init__(self, payload: RevRegDefCreateRequestedPayload):
        """Initialize an instance."""
        self._topic = self.event_topic
        self._payload = payload

    @classmethod
    def with_payload(
        cls,
        *,
        issuer_id: str,
        cred_def_id: str,
        registry_type: str,
        tag: str,
        max_cred_num: int,
        options: Optional[dict] = None,
    ):
        """With payload."""
        payload = RevRegDefCreateRequestedPayload(
            issuer_id=issuer_id,
            cred_def_id=cred_def_id,
            registry_type=registry_type,
            tag=tag,
            max_cred_num=max_cred_num,
            options=options or {},
        )
        return cls(payload)

    @property
    def payload(self) -> RevRegDefCreateRequestedPayload:
        """Return payload."""
        return self._payload


class RevRegDefCreateFailurePayload(NamedTuple):
    """Failure-specific payload for registry definition creation."""

    error_info: ErrorInfoPayload
    # Original request parameters needed for retry
    issuer_id: str
    cred_def_id: str
    registry_type: str
    tag: str
    max_cred_num: int


class RevRegDefCreateResponsePayload(NamedTuple):
    """Payload for rev reg def create response event."""

    # Success fields - populated when operation succeeds
    rev_reg_def_result: Optional[RevRegDefResult]
    rev_reg_def: Optional[RevRegDef]

    # Failure field - populated when operation fails
    failure: Optional[RevRegDefCreateFailurePayload]

    # Common options for both success and failure cases
    options: dict


class RevRegDefCreateResponseEvent(Event):
    """Event for rev reg def create response."""

    event_topic = REV_REG_DEF_CREATE_RESPONSE_EVENT

    def __init__(self, payload: RevRegDefCreateResponsePayload):
        """Initialize an instance."""
        self._topic = self.event_topic
        self._payload = payload

    @classmethod
    def with_payload(
        cls,
        *,
        # Success case parameters
        rev_reg_def_result: Optional[RevRegDefResult] = None,
        rev_reg_def: Optional[RevRegDef] = None,
        options: Optional[dict] = None,
        # Failure case parameters
        failure: Optional[RevRegDefCreateFailurePayload] = None,
    ):
        """With payload.

        For success: pass rev_reg_def_result, rev_reg_def
        For failure: pass failure=RevRegDefCreateFailurePayload(...)
        """
        payload = RevRegDefCreateResponsePayload(
            rev_reg_def_result=rev_reg_def_result,
            rev_reg_def=rev_reg_def,
            failure=failure,
            options=options or {},
        )
        return cls(payload)

    @classmethod
    def with_failure(
        cls,
        *,
        error_msg: str,
        should_retry: bool,
        retry_count: int,
        issuer_id: str,
        cred_def_id: str,
        registry_type: str,
        tag: str,
        max_cred_num: int,
        options: Optional[dict] = None,
    ):
        """Convenience method for creating failure response."""
        failure = RevRegDefCreateFailurePayload(
            error_info=ErrorInfoPayload(
                error_msg=error_msg,
                should_retry=should_retry,
                retry_count=retry_count,
            ),
            issuer_id=issuer_id,
            cred_def_id=cred_def_id,
            registry_type=registry_type,
            tag=tag,
            max_cred_num=max_cred_num,
        )
        return cls.with_payload(failure=failure, options=options)

    @property
    def payload(self) -> RevRegDefCreateResponsePayload:
        """Return payload."""
        return self._payload


class RevRegDefStoreRequestedPayload(NamedTuple):
    """Payload for rev reg def store requested event."""

    rev_reg_def: RevRegDef
    rev_reg_def_result: RevRegDefResult
    options: dict


class RevRegDefStoreRequestedEvent(Event):
    """Event for rev reg def store requested."""

    event_topic = REV_REG_DEF_STORE_REQUESTED_EVENT

    def __init__(self, payload: RevRegDefStoreRequestedPayload):
        """Initialize an instance."""
        self._topic = self.event_topic
        self._payload = payload

    @classmethod
    def with_payload(
        cls,
        *,
        rev_reg_def: RevRegDef,
        rev_reg_def_result: RevRegDefResult,
        options: Optional[dict] = None,
    ):
        """With payload."""
        payload = RevRegDefStoreRequestedPayload(
            rev_reg_def=rev_reg_def,
            rev_reg_def_result=rev_reg_def_result,
            options=options or {},
        )
        return cls(payload)

    @property
    def payload(self) -> RevRegDefStoreRequestedPayload:
        """Return payload."""
        return self._payload


class RevRegDefStoreFailurePayload(NamedTuple):
    """Failure-specific payload for registry definition store."""

    error_info: ErrorInfoPayload


class RevRegDefStoreResponsePayload(NamedTuple):
    """Payload for rev reg def store response event."""

    # Success fields - always populated with values that were requested to be stored
    rev_reg_def_id: str
    rev_reg_def: RevRegDef
    rev_reg_def_result: RevRegDefResult
    tag: str

    # Failure field - populated when operation fails
    failure: Optional[RevRegDefStoreFailurePayload]

    # Common options
    options: dict


class RevRegDefStoreResponseEvent(Event):
    """Event for rev reg def store response."""

    event_topic = REV_REG_DEF_STORE_RESPONSE_EVENT

    def __init__(self, payload: RevRegDefStoreResponsePayload):
        """Initialize an instance."""
        self._topic = self.event_topic
        self._payload = payload

    @classmethod
    def with_payload(
        cls,
        *,
        rev_reg_def_id: str,
        rev_reg_def: RevRegDef,
        rev_reg_def_result: RevRegDefResult,
        tag: str,
        failure: Optional[RevRegDefStoreFailurePayload] = None,
        options: Optional[dict] = None,
    ):
        """With payload.

        For success: pass rev_reg_def_id, rev_reg_def, rev_reg_def_result, tag
        For failure: pass failure=RevRegDefStoreFailurePayload(...)
        """
        payload = RevRegDefStoreResponsePayload(
            rev_reg_def_id=rev_reg_def_id,
            rev_reg_def=rev_reg_def,
            rev_reg_def_result=rev_reg_def_result,
            tag=tag,
            failure=failure,
            options=options or {},
        )
        return cls(payload)

    @classmethod
    def with_failure(
        cls,
        *,
        rev_reg_def_id: str,
        rev_reg_def: RevRegDef,
        rev_reg_def_result: RevRegDefResult,
        tag: str,
        error_msg: str,
        should_retry: bool,
        retry_count: int,
        options: Optional[dict] = None,
    ):
        """Convenience method for creating failure response."""
        failure = RevRegDefStoreFailurePayload(
            error_info=ErrorInfoPayload(
                error_msg=error_msg,
                should_retry=should_retry,
                retry_count=retry_count,
            ),
        )
        return cls.with_payload(
            rev_reg_def_id=rev_reg_def_id,
            rev_reg_def=rev_reg_def,
            rev_reg_def_result=rev_reg_def_result,
            tag=tag,
            failure=failure,
            options=options,
        )

    @property
    def payload(self) -> RevRegDefStoreResponsePayload:
        """Return payload."""
        return self._payload


class RevListCreateRequestedPayload(NamedTuple):
    """Payload for rev list create requested event."""

    rev_reg_def_id: str
    options: dict


class RevListCreateRequestedEvent(Event):
    """Event for rev list create requested."""

    event_topic = REV_LIST_CREATE_REQUESTED_EVENT

    def __init__(self, payload: RevListCreateRequestedPayload):
        """Initialize an instance."""
        self._topic = self.event_topic
        self._payload = payload

    @classmethod
    def with_payload(
        cls,
        rev_reg_def_id: str,
        options: Optional[dict] = None,
    ):
        """With payload."""
        payload = RevListCreateRequestedPayload(
            rev_reg_def_id=rev_reg_def_id,
            options=options or {},
        )
        return cls(payload)

    @property
    def payload(self) -> RevListCreateRequestedPayload:
        """Return payload."""
        return self._payload


class RevListCreateFailurePayload(NamedTuple):
    """Failure-specific payload for revocation list creation."""

    error_info: ErrorInfoPayload
    # Simple case: no extra retry parameters needed


class RevListCreateResponsePayload(NamedTuple):
    """Payload for rev list create response event."""

    # Success fields - always has rev_reg_def_id
    rev_reg_def_id: str
    rev_list_result: Optional[RevListResult]

    # Failure field - populated when operation fails
    failure: Optional[RevListCreateFailurePayload]

    # Common options
    options: dict


class RevListCreateResponseEvent(Event):
    """Event for rev list create response."""

    event_topic = REV_LIST_CREATE_RESPONSE_EVENT

    def __init__(self, payload: RevListCreateResponsePayload):
        """Initialize an instance."""
        self._topic = self.event_topic
        self._payload = payload

    @classmethod
    def with_payload(
        cls,
        rev_reg_def_id: str,
        rev_list_result: Optional[RevListResult] = None,
        failure: Optional[RevListCreateFailurePayload] = None,
        options: Optional[dict] = None,
    ):
        """With payload.

        For success: pass rev_reg_def_id and rev_list_result
        For failure: pass failure=RevListCreateFailurePayload(...)
        """
        payload = RevListCreateResponsePayload(
            rev_reg_def_id=rev_reg_def_id,
            rev_list_result=rev_list_result,
            failure=failure,
            options=options or {},
        )
        return cls(payload)

    @classmethod
    def with_failure(
        cls,
        rev_reg_def_id: str,
        error_msg: str,
        should_retry: bool = True,
        retry_count: int = 0,
        options: Optional[dict] = None,
    ):
        """Convenience method for creating failure response."""
        failure = RevListCreateFailurePayload(
            error_info=ErrorInfoPayload(
                error_msg=error_msg,
                should_retry=should_retry,
                retry_count=retry_count,
            )
        )
        return cls.with_payload(
            rev_reg_def_id=rev_reg_def_id,
            failure=failure,
            options=options,
        )

    @property
    def payload(self) -> RevListCreateResponsePayload:
        """Return payload."""
        return self._payload


class RevListStoreRequestedPayload(NamedTuple):
    """Payload for rev list store requested event."""

    rev_reg_def_id: str
    result: RevListResult
    options: dict


class RevListStoreRequestedEvent(Event):
    """Event for rev list store requested."""

    event_topic = REV_LIST_STORE_REQUESTED_EVENT

    def __init__(self, payload: RevListStoreRequestedPayload):
        """Initialize an instance."""
        self._topic = self.event_topic
        self._payload = payload

    @classmethod
    def with_payload(
        cls,
        *,
        rev_reg_def_id: str,
        result: RevListResult,
        options: Optional[dict] = None,
    ):
        """With payload."""
        payload = RevListStoreRequestedPayload(
            rev_reg_def_id=rev_reg_def_id,
            result=result,
            options=options or {},
        )
        return cls(payload)

    @property
    def payload(self) -> RevListStoreRequestedPayload:
        """Return payload."""
        return self._payload


class RevListStoreFailurePayload(NamedTuple):
    """Failure-specific payload for revocation list store."""

    error_info: ErrorInfoPayload


class RevListStoreResponsePayload(NamedTuple):
    """Payload for rev list store response event."""

    # Success fields - always has rev_reg_def_id and the requested RevListResult to store
    rev_reg_def_id: str
    result: RevListResult

    # Failure field - populated when operation fails
    failure: Optional[RevListStoreFailurePayload]

    # Common options
    options: dict


class RevListStoreResponseEvent(Event):
    """Event for rev list store response."""

    event_topic = REV_LIST_STORE_RESPONSE_EVENT

    def __init__(self, payload: RevListStoreResponsePayload):
        """Initialize an instance."""
        self._topic = self.event_topic
        self._payload = payload

    @classmethod
    def with_payload(
        cls,
        rev_reg_def_id: str,
        result: RevListResult,
        failure: Optional[RevListStoreFailurePayload] = None,
        options: Optional[dict] = None,
    ):
        """With payload.

        For success: pass rev_reg_def_id and result
        For failure: pass failure=RevListStoreFailurePayload(...)
        """
        payload = RevListStoreResponsePayload(
            rev_reg_def_id=rev_reg_def_id,
            result=result,
            failure=failure,
            options=options or {},
        )
        return cls(payload)

    @classmethod
    def with_failure(
        cls,
        rev_reg_def_id: str,
        result: RevListResult,
        error_msg: str,
        should_retry: bool,
        retry_count: int,
        options: Optional[dict] = None,
    ):
        """Convenience method for creating failure response."""
        failure = RevListStoreFailurePayload(
            error_info=ErrorInfoPayload(
                error_msg=error_msg,
                should_retry=should_retry,
                retry_count=retry_count,
            ),
        )
        return cls.with_payload(
            rev_reg_def_id=rev_reg_def_id,
            result=result,
            failure=failure,
            options=options,
        )

    @property
    def payload(self) -> RevListStoreResponsePayload:
        """Return payload."""
        return self._payload


class RevRegActivationRequestedPayload(NamedTuple):
    """Payload for rev reg activation requested event."""

    rev_reg_def_id: str
    options: dict


class RevRegActivationRequestedEvent(Event):
    """Event for rev reg activation requested."""

    event_topic = REV_REG_ACTIVATION_REQUESTED_EVENT

    def __init__(self, payload: RevRegActivationRequestedPayload):
        """Initialize an instance."""
        self._topic = self.event_topic
        self._payload = payload

    @classmethod
    def with_payload(
        cls,
        rev_reg_def_id: str,
        options: Optional[dict] = None,
    ):
        """With payload."""
        payload = RevRegActivationRequestedPayload(
            rev_reg_def_id=rev_reg_def_id,
            options=options or {},
        )
        return cls(payload)

    @property
    def payload(self) -> RevRegActivationRequestedPayload:
        """Return payload."""
        return self._payload


class RevRegActivationFailurePayload(NamedTuple):
    """Failure-specific payload for registry activation."""

    error_info: ErrorInfoPayload
    # Simple case: no extra retry parameters needed


class RevRegActivationResponsePayload(NamedTuple):
    """Payload for rev reg activation response event."""

    # Success field - always has rev_reg_def_id
    rev_reg_def_id: str

    # Failure field - populated when operation fails
    failure: Optional[RevRegActivationFailurePayload]

    # Common options
    options: dict


class RevRegActivationResponseEvent(Event):
    """Event for rev reg activation response."""

    event_topic = REV_REG_ACTIVATION_RESPONSE_EVENT

    def __init__(self, payload: RevRegActivationResponsePayload):
        """Initialize an instance."""
        self._topic = self.event_topic
        self._payload = payload

    @classmethod
    def with_payload(
        cls,
        rev_reg_def_id: str,
        failure: Optional[RevRegActivationFailurePayload] = None,
        options: Optional[dict] = None,
    ):
        """With payload.

        For success: just pass rev_reg_def_id
        For failure: pass failure=RevRegActivationFailurePayload(...)
        """
        payload = RevRegActivationResponsePayload(
            rev_reg_def_id=rev_reg_def_id,
            failure=failure,
            options=options or {},
        )
        return cls(payload)

    @classmethod
    def with_failure(
        cls,
        rev_reg_def_id: str,
        error_msg: str,
        should_retry: bool = True,
        retry_count: int = 0,
        options: Optional[dict] = None,
    ):
        """Convenience method for creating failure response."""
        failure = RevRegActivationFailurePayload(
            error_info=ErrorInfoPayload(
                error_msg=error_msg,
                should_retry=should_retry,
                retry_count=retry_count,
            )
        )
        return cls.with_payload(
            rev_reg_def_id=rev_reg_def_id,
            failure=failure,
            options=options,
        )

    @property
    def payload(self) -> RevRegActivationResponsePayload:
        """Return payload."""
        return self._payload


class RevRegFullDetectedPayload(NamedTuple):
    """Payload for rev reg full detected event."""

    rev_reg_def_id: str
    cred_def_id: str
    options: dict


class RevRegFullHandlingFailurePayload(NamedTuple):
    """Failure-specific payload for full registry handling."""

    error_info: ErrorInfoPayload
    # Simple case: no extra retry parameters needed


class RevRegFullDetectedEvent(Event):
    """Event for rev reg full detected."""

    event_topic = REV_REG_FULL_DETECTED_EVENT

    def __init__(self, payload: RevRegFullDetectedPayload):
        """Initialize an instance."""
        self._topic = self.event_topic
        self._payload = payload

    @classmethod
    def with_payload(
        cls,
        rev_reg_def_id: str,
        cred_def_id: str,
        options: Optional[dict] = None,
    ):
        """With payload."""
        payload = RevRegFullDetectedPayload(
            rev_reg_def_id=rev_reg_def_id,
            cred_def_id=cred_def_id,
            options=options or {},
        )
        return cls(payload)

    @property
    def payload(self) -> RevRegFullDetectedPayload:
        """Return payload."""
        return self._payload


class RevRegFullHandlingResponsePayload(NamedTuple):
    """Payload for rev reg full handling result event."""

    # Success fields - populated when operation succeeds
    old_rev_reg_def_id: str
    new_active_rev_reg_def_id: str
    cred_def_id: str

    # Failure field - populated when operation fails
    failure: Optional[RevRegFullHandlingFailurePayload]

    # Common options
    options: dict


class RevRegFullHandlingResponseEvent(Event):
    """Event for rev reg full handling result."""

    event_topic = REV_REG_FULL_HANDLING_COMPLETED_EVENT

    def __init__(self, payload: RevRegFullHandlingResponsePayload):
        """Initialize an instance."""
        self._topic = self.event_topic
        self._payload = payload

    @classmethod
    def with_payload(
        cls,
        *,
        old_rev_reg_def_id: str,
        new_active_rev_reg_def_id: str,
        cred_def_id: str,
        failure: Optional[RevRegFullHandlingFailurePayload] = None,
        options: Optional[dict] = None,
    ):
        """With payload.

        For success: pass old_rev_reg_def_id, new_active_rev_reg_def_id, cred_def_id
        For failure: pass failure=RevRegFullHandlingFailurePayload(...)
        """
        payload = RevRegFullHandlingResponsePayload(
            old_rev_reg_def_id=old_rev_reg_def_id,
            new_active_rev_reg_def_id=new_active_rev_reg_def_id,
            cred_def_id=cred_def_id,
            failure=failure,
            options=options or {},
        )
        return cls(payload)

    @classmethod
    def with_failure(
        cls,
        *,
        old_rev_reg_def_id: str,
        cred_def_id: str,
        error_msg: str,
        retry_count: int = 0,
        options: Optional[dict] = None,
    ):
        """Convenience method for creating failure response."""
        failure = RevRegFullHandlingFailurePayload(
            error_info=ErrorInfoPayload(
                error_msg=error_msg,
                should_retry=retry_count < 3,  # Default retry logic
                retry_count=retry_count,
            )
        )
        return cls.with_payload(
            old_rev_reg_def_id=old_rev_reg_def_id,
            new_active_rev_reg_def_id="",  # Empty on failure
            cred_def_id=cred_def_id,
            failure=failure,
            options=options,
        )

    @property
    def payload(self) -> RevRegFullHandlingResponsePayload:
        """Return payload."""
        return self._payload


class InterventionRequiredPayload(NamedTuple):
    """Payload for intervention required event."""

    point_of_failure: str
    error_msg: str
    identifier: str
    options: dict
