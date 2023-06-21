"""Events fired by AnonCreds interface."""

import re
from typing import NamedTuple, Optional

from aries_cloudagent.anoncreds.models.anoncreds_revocation import RevRegDef
from ..core.event_bus import Event


CRED_DEF_FINISHED_EVENT = "anoncreds::credential-definition::finished"
REV_REG_DEF_FINISHED_EVENT = "anoncreds::revocation-registry-definition::finished"
REV_LIST_FINISHED_EVENT = "anoncreds::revocation-list::finished"

CRED_DEF_FINISHED_PATTERN = re.compile("anoncreds::credential-definition::finished")
REV_REG_DEF_FINISHED_PATTERN = re.compile(
    "anoncreds::revocation-registry-definition::finished"
)
REV_LIST_FINISHED_PATTERN = re.compile("anoncreds::revocation-list::finished")


class CredDefFinishedPayload(NamedTuple):
    """Payload of cred def finished event."""

    schema_id: str
    cred_def_id: str
    issuer_id: str
    support_revocation: bool
    novel: bool
    max_cred_num: int
    auto_create_rev_reg: bool = False
    create_pending_rev_reg: bool = False


class CredDefFinishedEvent(Event):
    """Event for cred def finished."""

    def __init__(self, payload: CredDefFinishedPayload):
        self._topic = CRED_DEF_FINISHED_EVENT
        self._payload = payload

    @property
    def payload(self) -> CredDefFinishedPayload:
        """Return payload."""
        return self._payload


class RevRegDefFinishedPayload(NamedTuple):
    """Payload of rev reg def finished event."""

    rev_reg_def_id: str
    rev_reg_def: RevRegDef


class RevRegDefFinishedEvent(Event):
    """Event for rev reg def finished."""

    def __init__(self, payload: RevRegDefFinishedPayload):
        self._topic = REV_REG_DEF_FINISHED_EVENT
        self._payload = payload

    @property
    def payload(self) -> RevRegDefFinishedPayload:
        """Return payload."""
        return self._payload


class RevListFinishedPayload(NamedTuple):
    """Payload of rev list finished event."""


class RevListFinishedEvent(Event):
    """Event for rev list finished."""

    def __init__(self, payload: RevListFinishedPayload):
        self._topic = REV_LIST_FINISHED_EVENT
        self._payload = payload

    @property
    def payload(self) -> RevListFinishedPayload:
        """Return payload."""
        return self._payload
