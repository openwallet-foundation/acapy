"""Model for representing a stored verifiable credential."""

import json

from pyld import jsonld
from pyld.jsonld import JsonLdProcessor
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
        # one or more credential schema IDs may be present
        schema_ids: Sequence[str],
        # the credential encoded as a serialized JSON string
        value: str,
        # value of the credential 'id' property, if any
        given_id: str = None,
        # array of tags for retrieval (derived from attribute values)
        tags: dict = None,
        # specify the storage record ID
        record_id: str = None,
    ):
        """Initialize some defaults on record."""
        self.contexts = set(contexts) if contexts else set()
        self.types = set(types) if types else set()
        self.schema_ids = set(schema_ids) if schema_ids else set()
        self.issuer_id = issuer_id
        self.subject_ids = set(subject_ids) if subject_ids else set()
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
            and other.schema_ids == self.schema_ids
            and other.issuer_id == self.issuer_id
            and other.given_id == self.given_id
            and other.record_id == self.record_id
            and other.tags == self.tags
            and other.value == self.value
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
            value=value,
            tags=tags,
            record_id=record_id,
            schema_ids=schema_ids,
        )
