"""Model for representing a stored verifiable credential."""

from typing import Sequence
from uuid import uuid4


class VCRecord:
    """Verifiable credential storage record class."""

    def __init__(
        self,
        *,
        # context is required by spec
        contexts: Sequence[str],
        # type is required by spec
        types: Sequence[str],
        # issuer ID is required by spec
        issuer_id: str,
        # one or more subject IDs may be present
        subject_ids: Sequence[str],
        # credential encoded as a string
        value: str,
        # value of the credential 'id' property, if any
        given_id: str = None,
        # array of tags for retrieval (derived from attribute values)
        tags: dict = None,
        # specify the storage record ID
        record_id: str = None,
    ):
        """Initialize some defaults on record."""
        self.contexts = list(contexts) if contexts else []
        self.types = list(types) if types else []
        self.issuer_id = issuer_id
        self.subject_ids = list(subject_ids) if subject_ids else []
        self.value = value
        self.given_id = given_id
        self.tags = tags or {}
        self.record_id = record_id or uuid4().hex

    def __eq__(self, other: object) -> bool:
        """Compare two VC records for equality."""
        if not isinstance(other, VCRecord):
            return False
        return (
            other.contexts == self.contexts
            and other.types == self.types
            and other.subject_ids == self.subject_ids
            and other.issuer_id == self.issuer_id
            and other.given_id == self.given_id
            and other.record_id == self.record_id
            and other.tags == self.tags
            and other.value == self.value
        )
