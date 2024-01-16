"""Events fired by AnonCreds interface."""

import re
from typing import NamedTuple

from ..core.event_bus import Event
from .models.anoncreds_revocation import RevRegDef

CRED_DEF_FINISHED_EVENT = "anoncreds::credential-definition::finished"
REV_REG_DEF_FINISHED_EVENT = "anoncreds::revocation-registry-definition::finished"
REV_LIST_FINISHED_EVENT = "anoncreds::revocation-list::finished"
SCHEMA_REGISTRATION_FINISHED_EVENT = "anoncreds::schema::registration::finished"

CRED_DEF_FINISHED_PATTERN = re.compile(CRED_DEF_FINISHED_EVENT)
REV_REG_DEF_FINISHED_PATTERN = re.compile(REV_REG_DEF_FINISHED_EVENT)
REV_LIST_FINISHED_PATTERN = re.compile(REV_LIST_FINISHED_EVENT)
SCHEMA_REGISTRATION_FINISHED_PATTERN = re.compile(SCHEMA_REGISTRATION_FINISHED_EVENT)


class CredDefFinishedPayload(NamedTuple):
    """Payload of cred def finished event."""

    schema_id: str
    cred_def_id: str
    issuer_id: str
    support_revocation: bool
    max_cred_num: int


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
    ):
        """With payload."""
        payload = CredDefFinishedPayload(
            schema_id, cred_def_id, issuer_id, support_revocation, max_cred_num
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
    ):
        """With payload."""
        payload = RevRegDefFinishedPayload(rev_reg_def_id, rev_reg_def)
        return cls(payload)

    @property
    def payload(self) -> RevRegDefFinishedPayload:
        """Return payload."""
        return self._payload


class RevListFinishedPayload(NamedTuple):
    """Payload of rev list finished event."""


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

    @property
    def payload(self) -> RevListFinishedPayload:
        """Return payload."""
        return self._payload


class SchemaRegistrationFinishedPayload(NamedTuple):
    """Payload of schema transaction event."""

    meta_data: dict


class SchemaRegistrationFinishedEvent(Event):
    """Event for schema post-process."""

    def __init__(self, payload: SchemaRegistrationFinishedPayload):
        """Initialize an instance.

        Args:
            schema_id: schema id
            meta_data: meta data
        """
        self._topic = SCHEMA_REGISTRATION_FINISHED_EVENT
        self._payload = payload

    @classmethod
    def with_payload(cls, meta_data: dict):
        """With payload."""
        payload = SchemaRegistrationFinishedPayload(meta_data)
        return cls(payload)

    @property
    def payload(self) -> SchemaRegistrationFinishedPayload:
        """Return payload."""
        return self._payload
