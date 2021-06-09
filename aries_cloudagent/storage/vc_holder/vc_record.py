"""Model for representing a stored verifiable credential."""

import logging

from typing import Mapping, Sequence
from uuid import uuid4

from marshmallow import EXCLUDE, fields

from ...messaging.models.base import BaseModel, BaseModelSchema
from ...messaging.valid import ENDPOINT, UUIDFour

LOGGER = logging.getLogger(__name__)


class VCRecord(BaseModel):
    """Verifiable credential storage record class."""

    class Meta:
        """VCRecord metadata."""

        schema_class = "VCRecordSchema"

    def __init__(
        self,
        *,
        contexts: Sequence[str],  # context is required by spec
        expanded_types: Sequence[str],  # expanded type from contexts and types
        issuer_id: str,  # issuer ID is required by spec
        subject_ids: Sequence[str],  # one or more subject IDs may be present
        schema_ids: Sequence[str],  # one or more credential schema IDs may be present
        proof_types: Sequence[str],  # one or more proof types may be present
        cred_value: Mapping,  # the credential value as a JSON-serializable mapping
        given_id: str = None,  # value of the credential 'id' property, if any
        cred_tags: Mapping = None,  # tags for retrieval (derived from attribute values)
        record_id: str = None,  # specify the storage record ID
    ):
        """Initialize some defaults on record."""
        super().__init__()
        self.contexts = set(contexts) if contexts else set()
        self.expanded_types = set(expanded_types) if expanded_types else set()
        self.schema_ids = set(schema_ids) if schema_ids else set()
        self.issuer_id = issuer_id
        self.subject_ids = set(subject_ids) if subject_ids else set()
        self.proof_types = set(proof_types) if proof_types else set()
        self.cred_value = cred_value
        self.given_id = given_id
        self.cred_tags = cred_tags or {}
        self.record_id = record_id or uuid4().hex

    def serialize(self, as_string=False) -> dict:
        """
        Create a JSON-compatible dict representation of the model instance.

        Args:
            as_string: Return a string of JSON instead of a dict

        Returns:
            A dict representation of this model, or a JSON string if as_string is True

        """

        list_coercion = VCRecord(**{k: v for k, v in vars(self).items()})
        for k, v in vars(self).items():
            if isinstance(v, set):
                setattr(list_coercion, k, list(v))

        return super(VCRecord, list_coercion).serialize(as_string=as_string)

    def __eq__(self, other: object) -> bool:
        """Compare two VC records for equality."""
        if not isinstance(other, VCRecord):
            return False
        return (
            other.contexts == self.contexts
            and other.expanded_types == self.expanded_types
            and other.subject_ids == self.subject_ids
            and other.schema_ids == self.schema_ids
            and other.issuer_id == self.issuer_id
            and other.proof_types == self.proof_types
            and other.given_id == self.given_id
            and other.record_id == self.record_id
            and other.cred_tags == self.cred_tags
            and other.cred_value == self.cred_value
        )


class VCRecordSchema(BaseModelSchema):
    """Verifiable credential storage record schema class."""

    class Meta:
        """Verifiable credential storage record schema metadata."""

        model_class = VCRecord
        unknown = EXCLUDE

    contexts = fields.List(fields.Str(description="Context", **ENDPOINT))
    expanded_types = fields.List(
        fields.Str(
            description="JSON-LD expanded type extracted from type and context",
            example="https://w3id.org/citizenship#PermanentResidentCard",
        ),
    )
    schema_ids = fields.List(
        fields.Str(
            description="Schema identifier",
            example="https://example.org/examples/degree.json",
        )
    )
    issuer_id = fields.Str(
        description="Issuer identifier",
        example="https://example.edu/issuers/14",
    )
    subject_ids = fields.List(
        fields.Str(
            description="Subject identifier",
            example="did:example:ebfeb1f712ebc6f1c276e12ec21",
        )
    )
    proof_types = fields.List(
        fields.Str(
            description="Signature suite used for proof", example="Ed25519Signature2018"
        )
    )

    cred_value = fields.Dict(description="(JSON-serializable) credential value")
    given_id = fields.Str(
        description="Credential identifier",
        example="http://example.edu/credentials/3732",
    )
    cred_tags = fields.Dict(
        keys=fields.Str(description="Retrieval tag name"),
        values=fields.Str(description="Retrieval tag value"),
    )
    record_id = fields.Str(description="Record identifier", example=UUIDFour.EXAMPLE)
