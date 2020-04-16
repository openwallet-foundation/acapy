"""Schema utilities."""

from ..valid import IndySchemaId, IndyDID, IndyVersion

SCHEMA_TAGS = {
    "schema_id": IndySchemaId.PATTERN,
    "schema_issuer_did": IndyDID.PATTERN,
    "schema_name": "^.+$",
    "schema_version": IndyVersion.PATTERN,
}
SCHEMA_SENT_RECORD_TYPE = "schema_sent"
