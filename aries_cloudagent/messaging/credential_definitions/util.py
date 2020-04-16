"""Credential definition utilities."""

from ..valid import IndySchemaId, IndyDID, IndyVersion, IndyCredDefId

CRED_DEF_TAGS = {
    "schema_id": IndySchemaId.PATTERN,
    "schema_issuer_did": IndyDID.PATTERN,
    "schema_name": "^.+$",
    "schema_version": IndyVersion.PATTERN,
    "issuer_did": IndyDID.PATTERN,
    "cred_def_id": IndyCredDefId.PATTERN,
}
CRED_DEF_SENT_RECORD_TYPE = "cred_def_sent"
