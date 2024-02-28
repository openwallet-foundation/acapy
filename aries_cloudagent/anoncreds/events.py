"""Events fired by AnonCreds interface."""

import re
from typing import NamedTuple, Optional

from ..core.event_bus import Event
from .models.anoncreds_revocation import RevRegDef

CRED_DEF_FINISHED_EVENT = "anoncreds::credential-definition::finished"
REV_REG_DEF_FINISHED_EVENT = "anoncreds::revocation-registry-definition::finished"
REV_LIST_FINISHED_EVENT = "anoncreds::revocation-list::finished"

CRED_DEF_FINISHED_PATTERN = re.compile(CRED_DEF_FINISHED_EVENT)
REV_REG_DEF_FINISHED_PATTERN = re.compile(REV_REG_DEF_FINISHED_EVENT)
REV_LIST_FINISHED_PATTERN = re.compile(REV_LIST_FINISHED_EVENT)


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

    def __init__(
        self,
        payload: CredDefFinishedPayload,
    ):
        """Initialize an instance.

        Args:
            payload: CredDefFinishedPayload

        TODO: update this docstring - Anoncreds-break.

        """
        self._topic = CRED_DEF_FINISHED_EVENT
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
            schema_id, cred_def_id, issuer_id, support_revocation, max_cred_num, options
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

    def __init__(self, payload: RevRegDefFinishedPayload):
        """Initialize an instance.

        Args:
            payload: RevRegDefFinishedPayload

        TODO: update this docstring - Anoncreds-break.

        """
        self._topic = REV_REG_DEF_FINISHED_EVENT
        self._payload = payload

    @classmethod
    def with_payload(
        cls,
        rev_reg_def_id: str,
        rev_reg_def: RevRegDef,
        options: Optional[dict] = None,
    ):
        """With payload."""
        payload = RevRegDefFinishedPayload(rev_reg_def_id, rev_reg_def, options)
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

    def __init__(self, payload: RevListFinishedPayload):
        """Initialize an instance.

        Args:
            payload: RevListFinishedPayload

        TODO: update this docstring - Anoncreds-break.

        """
        self._topic = REV_LIST_FINISHED_EVENT
        self._payload = payload

    @classmethod
    def with_payload(
        cls,
        rev_reg_id: str,
        revoked: list,
        options: Optional[dict] = None,
    ):
        """With payload."""
        payload = RevListFinishedPayload(rev_reg_id, revoked, options)
        return cls(payload)

    @property
    def payload(self) -> RevListFinishedPayload:
        """Return payload."""
        return self._payload
