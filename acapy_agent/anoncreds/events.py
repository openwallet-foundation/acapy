"""Events fired by AnonCreds interface."""

from typing import NamedTuple, Optional

from anoncreds import RevocationRegistryDefinitionPrivate

from ..core.event_bus import Event
from .models.revocation import RevListResult, RevRegDef, RevRegDefResult

# Initial credential definition event, kicks off the revocation setup process
CRED_DEF_FINISHED_EVENT = "anoncreds::credential-definition::finished"

# Revocation registry definition events
REV_REG_DEF_CREATE_REQUESTED_EVENT = (
    "anoncreds::revocation-registry-definition::create-requested"
)
REV_REG_DEF_CREATE_RESPONSE_EVENT = (
    "anoncreds::revocation-registry-definition::create-response"
)

# Store the rev reg result events
REV_REG_DEF_STORE_REQUESTED_EVENT = (
    "anoncreds::revocation-registry-definition::store-requested"
)
REV_REG_DEF_STORE_RESPONSE_EVENT = (
    "anoncreds::revocation-registry-definition::store-response"
)

# Successful storage of rev reg def, triggers upload tails file event
REV_REG_DEF_FINISHED_EVENT = "anoncreds::revocation-registry-definition::finished"

# Tails upload events
TAILS_UPLOAD_REQUESTED_EVENT = "anoncreds::tails-upload::requested"
TAILS_UPLOAD_RESPONSE_EVENT = "anoncreds::tails-upload::response"

# Revocation list events
REV_LIST_CREATE_REQUESTED_EVENT = "anoncreds::revocation-list::create-requested"
REV_LIST_CREATE_RESPONSE_EVENT = "anoncreds::revocation-list::create-response"
REV_LIST_STORE_REQUESTED_EVENT = "anoncreds::revocation-list::store-requested"
REV_LIST_STORE_RESPONSE_EVENT = "anoncreds::revocation-list::store-response"
REV_LIST_FINISHED_EVENT = "anoncreds::revocation-list::finished"

# Revocation registry activation events
REV_REG_ACTIVATION_REQUESTED_EVENT = (
    "anoncreds::revocation-registry::activation-requested"
)
REV_REG_ACTIVATION_RESPONSE_EVENT = "anoncreds::revocation-registry::activation-response"

# Revocation registry full events
REV_REG_FULL_DETECTED_EVENT = "anoncreds::revocation-registry::full-detected"
REV_REG_FULL_HANDLING_STARTED_EVENT = (
    "anoncreds::revocation-registry::full-handling-started"
)
REV_REG_FULL_HANDLING_COMPLETED_EVENT = (
    "anoncreds::revocation-registry::full-handling-completed"
)
REV_REG_FULL_HANDLING_FAILED_EVENT = (
    "anoncreds::revocation-registry::full-handling-failed"
)

FIRST_REGISTRY_TAG = str(0)  # This tag is used to signify it is the first registry


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


class RevRegDefCreateResponsePayload(NamedTuple):
    """Payload for rev reg def create response event."""

    # Following fields are for handling success cases
    rev_reg_def_result: Optional[RevRegDefResult]
    rev_reg_def: Optional[RevRegDef]
    rev_reg_def_private: Optional[RevocationRegistryDefinitionPrivate]
    options: dict

    # Following fields are for handling failure cases
    issuer_id: Optional[str]
    cred_def_id: Optional[str]
    registry_type: Optional[str]
    tag: Optional[str]
    max_cred_num: Optional[int]
    error_msg: Optional[str]
    should_retry: bool
    retry_count: int


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
        # Following fields are for handling success cases
        rev_reg_def_result: Optional[RevRegDefResult] = None,
        rev_reg_def: Optional[RevRegDef] = None,
        rev_reg_def_private: Optional[RevocationRegistryDefinitionPrivate] = None,
        options: Optional[dict] = None,
        # Following fields are for handling failure cases
        issuer_id: Optional[str] = None,
        cred_def_id: Optional[str] = None,
        registry_type: Optional[str] = None,
        tag: Optional[str] = None,
        max_cred_num: Optional[int] = None,
        error_msg: Optional[str] = None,
        should_retry: bool = False,
        retry_count: int = 0,
    ):
        """With payload."""
        payload = RevRegDefCreateResponsePayload(
            rev_reg_def_result=rev_reg_def_result,
            rev_reg_def=rev_reg_def,
            rev_reg_def_private=rev_reg_def_private,
            options=options or {},
            issuer_id=issuer_id,
            cred_def_id=cred_def_id,
            registry_type=registry_type,
            tag=tag,
            max_cred_num=max_cred_num,
            error_msg=error_msg,
            should_retry=should_retry,
            retry_count=retry_count,
        )
        return cls(payload)

    @property
    def payload(self) -> RevRegDefCreateResponsePayload:
        """Return payload."""
        return self._payload


class RevRegDefStoreRequestedPayload(NamedTuple):
    """Payload for rev reg def store requested event."""

    rev_reg_def: RevRegDef
    rev_reg_def_result: RevRegDefResult
    rev_reg_def_private: RevocationRegistryDefinitionPrivate
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
        rev_reg_def_private: RevocationRegistryDefinitionPrivate,
        options: Optional[dict] = None,
    ):
        """With payload."""
        payload = RevRegDefStoreRequestedPayload(
            rev_reg_def=rev_reg_def,
            rev_reg_def_result=rev_reg_def_result,
            rev_reg_def_private=rev_reg_def_private,
            options=options or {},
        )
        return cls(payload)

    @property
    def payload(self) -> RevRegDefStoreRequestedPayload:
        """Return payload."""
        return self._payload


class RevRegDefStoreResponsePayload(NamedTuple):
    """Payload for rev reg def store response event."""

    # Following fields are for handling success cases
    rev_reg_def_id: Optional[str]
    rev_reg_def: RevRegDef
    rev_reg_def_result: Optional[RevRegDefResult]
    tag: str
    options: dict

    # Following fields are for handling failure cases
    rev_reg_def_private: Optional[RevocationRegistryDefinitionPrivate]
    error_msg: Optional[str]
    should_retry: bool
    retry_count: int


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
        rev_reg_def_result: Optional[RevRegDefResult] = None,
        tag: str,
        rev_reg_def_private: Optional[RevocationRegistryDefinitionPrivate] = None,
        error_msg: Optional[str] = None,
        should_retry: bool = False,
        retry_count: int = 0,
        options: Optional[dict] = None,
    ):
        """With payload."""
        payload = RevRegDefStoreResponsePayload(
            rev_reg_def_id=rev_reg_def_id,
            rev_reg_def=rev_reg_def,
            rev_reg_def_result=rev_reg_def_result,
            tag=tag,
            rev_reg_def_private=rev_reg_def_private,
            error_msg=error_msg,
            should_retry=should_retry,
            retry_count=retry_count,
            options=options or {},
        )
        return cls(payload)

    @property
    def payload(self) -> RevRegDefStoreResponsePayload:
        """Return payload."""
        return self._payload


class TailsUploadRequestedPayload(NamedTuple):
    """Payload for tails upload requested event."""

    rev_reg_def_id: str
    rev_reg_def: RevRegDef
    options: dict


class TailsUploadRequestedEvent(Event):
    """Event for tails upload requested."""

    event_topic = TAILS_UPLOAD_REQUESTED_EVENT

    def __init__(self, payload: TailsUploadRequestedPayload):
        """Initialize an instance."""
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
        payload = TailsUploadRequestedPayload(
            rev_reg_def_id=rev_reg_def_id,
            rev_reg_def=rev_reg_def,
            options=options or {},
        )
        return cls(payload)

    @property
    def payload(self) -> TailsUploadRequestedPayload:
        """Return payload."""
        return self._payload


class TailsUploadResponsePayload(NamedTuple):
    """Payload for tails upload response event."""

    rev_reg_def_id: str
    rev_reg_def: RevRegDef
    error_msg: Optional[str]
    should_retry: bool
    retry_count: int
    options: dict


class TailsUploadResponseEvent(Event):
    """Event for tails upload response."""

    event_topic = TAILS_UPLOAD_RESPONSE_EVENT

    def __init__(self, payload: TailsUploadResponsePayload):
        """Initialize an instance."""
        self._topic = self.event_topic
        self._payload = payload

    @classmethod
    def with_payload(
        cls,
        rev_reg_def_id: str,
        rev_reg_def: RevRegDef,
        error_msg: Optional[str] = None,
        should_retry: bool = False,
        retry_count: int = 0,
        options: Optional[dict] = None,
    ):
        """With payload."""
        payload = TailsUploadResponsePayload(
            rev_reg_def_id,
            rev_reg_def,
            error_msg,
            should_retry,
            retry_count,
            options or {},
        )
        return cls(payload)

    @property
    def payload(self) -> TailsUploadResponsePayload:
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
        payload = RevListCreateRequestedPayload(rev_reg_def_id, options or {})
        return cls(payload)

    @property
    def payload(self) -> RevListCreateRequestedPayload:
        """Return payload."""
        return self._payload


class RevListCreateResponsePayload(NamedTuple):
    """Payload for rev list create response event."""

    rev_reg_def_id: str
    rev_list_result: Optional[RevListResult]
    error_msg: Optional[str]
    should_retry: bool
    retry_count: int
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
        error_msg: Optional[str] = None,
        should_retry: bool = False,
        retry_count: int = 0,
        options: Optional[dict] = None,
    ):
        """With payload."""
        payload = RevListCreateResponsePayload(
            rev_reg_def_id,
            rev_list_result,
            error_msg,
            should_retry,
            retry_count,
            options or {},
        )
        return cls(payload)

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
        payload = RevListStoreRequestedPayload(rev_reg_def_id, result, options or {})
        return cls(payload)

    @property
    def payload(self) -> RevListStoreRequestedPayload:
        """Return payload."""
        return self._payload


class RevListStoreResponsePayload(NamedTuple):
    """Payload for rev list store response event."""

    rev_reg_def_id: str
    result: Optional[RevListResult]
    error_msg: Optional[str]
    should_retry: bool
    retry_count: int
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
        result: Optional[RevListResult] = None,
        error_msg: Optional[str] = None,
        should_retry: bool = False,
        retry_count: int = 0,
        options: Optional[dict] = None,
    ):
        """With payload."""
        payload = RevListStoreResponsePayload(
            rev_reg_def_id,
            result,
            error_msg,
            should_retry,
            retry_count,
            options or {},
        )
        return cls(payload)

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
        payload = RevRegActivationRequestedPayload(rev_reg_def_id, options or {})
        return cls(payload)

    @property
    def payload(self) -> RevRegActivationRequestedPayload:
        """Return payload."""
        return self._payload


class RevRegActivationResponsePayload(NamedTuple):
    """Payload for rev reg activation response event."""

    rev_reg_def_id: str
    error_msg: Optional[str]
    should_retry: bool
    retry_count: int
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
        error_msg: Optional[str] = None,
        should_retry: bool = False,
        retry_count: int = 0,
        options: Optional[dict] = None,
    ):
        """With payload."""
        payload = RevRegActivationResponsePayload(
            rev_reg_def_id, error_msg, should_retry, retry_count, options or {}
        )
        return cls(payload)

    @property
    def payload(self) -> RevRegActivationResponsePayload:
        """Return payload."""
        return self._payload


class RevRegFullDetectedPayload(NamedTuple):
    """Payload for rev reg full detected event."""

    rev_reg_def_id: str
    cred_def_id: str
    options: dict


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
        payload = RevRegFullDetectedPayload(rev_reg_def_id, cred_def_id, options or {})
        return cls(payload)

    @property
    def payload(self) -> RevRegFullDetectedPayload:
        """Return payload."""
        return self._payload


class RevRegFullHandlingResponsePayload(NamedTuple):
    """Payload for rev reg full handling result event."""

    old_rev_reg_def_id: str
    new_active_rev_reg_def_id: str
    new_backup_rev_reg_def_id: str
    cred_def_id: str
    options: dict
    error_msg: str
    retry_count: int


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
        new_backup_rev_reg_def_id: str,
        cred_def_id: str,
        options: Optional[dict] = None,
        error_msg: str = "",
        retry_count: int = 0,
    ):
        """With payload."""
        payload = RevRegFullHandlingResponsePayload(
            old_rev_reg_def_id=old_rev_reg_def_id,
            new_active_rev_reg_def_id=new_active_rev_reg_def_id,
            new_backup_rev_reg_def_id=new_backup_rev_reg_def_id,
            cred_def_id=cred_def_id,
            options=options or {},
            error_msg=error_msg,
            retry_count=retry_count,
        )
        return cls(payload)

    @property
    def payload(self) -> RevRegFullHandlingResponsePayload:
        """Return payload."""
        return self._payload
