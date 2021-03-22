"""De/serialization between StorageRecord and VCRecord."""

from aries_cloudagent.storage.record import StorageRecord

from .vc_record import VCRecord

VC_CRED_RECORD_TYPE = "vc_cred"


def load_credential(record: StorageRecord) -> VCRecord:
    """Convert an Indy-SDK stored record into a VC record."""
    cred_tags = {}
    contexts = []
    types = []
    schema_ids = []
    subject_ids = []
    issuer_id = None
    given_id = None
    for tagname, tagval in (record.tags or {}).items():
        if tagname.startswith("ctxt:"):
            contexts.append(tagname[5:])
        elif tagname.startswith("type:"):
            types.append(tagname[5:])
        elif tagname.startswith("schm:"):
            schema_ids.append(tagname[5:])
        elif tagname.startswith("subj:"):
            subject_ids.append(tagname[5:])
        elif tagname == "issuer_id":
            issuer_id = tagval
        elif tagname == "given_id":
            given_id = tagval
        else:
            cred_tags[tagname] = tagval
    return VCRecord(
        contexts=contexts,
        types=types,
        schema_ids=schema_ids,
        issuer_id=issuer_id,
        subject_ids=subject_ids,
        value_json=record.value,
        given_id=given_id,
        cred_tags=cred_tags,
        record_id=record.id,
    )


def serialize_credential(cred: VCRecord) -> StorageRecord:
    """Convert a VC record into an in-memory stored record."""
    tags = {}
    for ctx_val in cred.contexts:
        tags[f"ctxt:{ctx_val}"] = "1"
    for type_val in cred.types:
        tags[f"type:{type_val}"] = "1"
    for schema_val in cred.schema_ids:
        tags[f"schm:{schema_val}"] = "1"
    for subj_id in cred.subject_ids:
        tags[f"subj:{subj_id}"] = "1"
    if cred.issuer_id:
        tags["issuer_id"] = cred.issuer_id
    if cred.given_id:
        tags["given_id"] = cred.given_id
    if cred.cred_tags:
        tags.update(cred.cred_tags)
    return StorageRecord(VC_CRED_RECORD_TYPE, cred.value_json, tags, cred.record_id)
