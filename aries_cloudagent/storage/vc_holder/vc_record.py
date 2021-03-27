"""Model for representing a stored verifiable credential."""

import json

from pyld import jsonld
from pyld.jsonld import JsonLdProcessor
import logging

from typing import Mapping, Sequence, Sequence
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
        types: Sequence[str],  # type is required by spec
        issuer_id: str,  # issuer ID is required by spec
        subject_ids: Sequence[str],  # one or more subject IDs may be present
        schema_ids: Sequence[str],  # one or more credential schema IDs may be present
        cred_value: Mapping,  # the credential value as a JSON-serializable mapping
        given_id: str = None,  # value of the credential 'id' property, if any
        cred_tags: Mapping = None,  # tags for retrieval (derived from attribute values)
        record_id: str = None,  # specify the storage record ID
    ):
        """Initialize some defaults on record."""
        super().__init__()
        self.contexts = set(contexts) if contexts else set()
        self.types = set(types) if types else set()
        self.schema_ids = set(schema_ids) if schema_ids else set()
        self.issuer_id = issuer_id
        self.subject_ids = set(subject_ids) if subject_ids else set()
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
            and other.types == self.types
            and other.subject_ids == self.subject_ids
            and other.schema_ids == self.schema_ids
            and other.issuer_id == self.issuer_id
            and other.given_id == self.given_id
            and other.record_id == self.record_id
            and other.cred_tags == self.cred_tags
            and other.cred_value == self.cred_value
        )

    @classmethod
    def deserialize_jsonld_cred(cls, cred_json: str) -> "VCRecord":
        """
        Return VCRecord.

        Deserialize JSONLD cred to a VCRecord

        Args:
            cred_json: credential json string
        Return:
            VCRecord

        """
        given_id = None
        tags = None
        value = ""
        record_id = None
        subject_ids = set()
        issuer_id = ""
        contexts = set()
        types = set()
        schema_ids = set()
        cred_dict = json.loads(cred_json)
        if "vc" in cred_dict:
            cred_dict = cred_dict.get("vc")
        if "id" in cred_dict:
            given_id = cred_dict.get("id")
        if "@context" in cred_dict:
            # Should not happen
            if type(cred_dict.get("@context")) is not list:
                if type(cred_dict.get("@context")) is str:
                    contexts.add(cred_dict.get("@context"))
            else:
                for tmp_item in cred_dict.get("@context"):
                    if type(tmp_item) is str:
                        contexts.add(tmp_item)
        if "issuer" in cred_dict:
            if type(cred_dict.get("issuer")) is dict:
                issuer_id = cred_dict.get("issuer").get("id")
            else:
                issuer_id = cred_dict.get("issuer")
        if "type" in cred_dict:
            expanded = jsonld.expand(cred_dict)
            types = JsonLdProcessor.get_values(
                expanded[0],
                "@type",
            )
        if "credentialSubject" in cred_dict:
            if type(cred_dict.get("credentialSubject")) is list:
                tmp_list = cred_dict.get("credentialSubject")
                for tmp_dict in tmp_list:
                    subject_ids.add(tmp_dict.get("id"))
            elif type(cred_dict.get("credentialSubject")) is dict:
                tmp_dict = cred_dict.get("credentialSubject")
                subject_ids.add(tmp_dict.get("id"))
            elif type(cred_dict.get("credentialSubject")) is str:
                subject_ids.add(cred_dict.get("credentialSubject"))
        if "credentialSchema" in cred_dict:
            if type(cred_dict.get("credentialSchema")) is list:
                tmp_list = cred_dict.get("credentialSchema")
                for tmp_dict in tmp_list:
                    schema_ids.add(tmp_dict.get("id"))
            elif type(cred_dict.get("credentialSchema")) is dict:
                tmp_dict = cred_dict.get("credentialSchema")
                schema_ids.add(tmp_dict.get("id"))
            elif type(cred_dict.get("credentialSchema")) is str:
                schema_ids.add(cred_dict.get("credentialSchema"))
        value = cred_json
        return VCRecord(
            contexts=contexts,
            types=types,
            issuer_id=issuer_id,
            subject_ids=subject_ids,
            given_id=given_id,
            cred_value=value,
            cred_tags=tags,
            record_id=record_id,
            schema_ids=schema_ids,
        )


class VCRecordSchema(BaseModelSchema):
    """Verifiable credential storage record schema class."""

    class Meta:
        """Verifiable credential storage record schema metadata."""

        model_class = VCRecord
        unknown = EXCLUDE

    contexts = fields.List(fields.Str(description="Context", **ENDPOINT))
    types = fields.List(
        fields.Str(
            description="Type",
            example="VerifiableCredential",
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
