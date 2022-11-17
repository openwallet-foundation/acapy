"""Transformation between StorageRecord and VCRecord."""

import json

from ...storage.record import StorageRecord

from .vc_record import VCRecord

VC_CRED_RECORD_TYPE = "vc_cred"


def storage_to_vc_record(record: StorageRecord) -> VCRecord:
    """Convert an Indy-SDK stored record into a VC record."""
    cred_tags = {}
    contexts = []
    types = []
    schema_ids = []
    subject_ids = []
    proof_types = []
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
        elif tagname.startswith("ptyp:"):
            proof_types.append(tagname[5:])
        elif tagname == "issuer_id":
            issuer_id = tagval
        elif tagname == "given_id":
            given_id = tagval
        else:
            cred_tags[tagname] = tagval
    return VCRecord(
        contexts=contexts,
        expanded_types=types,
        schema_ids=schema_ids,
        issuer_id=issuer_id,
        subject_ids=subject_ids,
        proof_types=proof_types,
        cred_value=json.loads(record.value),
        given_id=given_id,
        cred_tags=cred_tags,
        record_id=record.id,
    )


def vc_to_storage_record(cred: VCRecord) -> StorageRecord:
    """Convert a VC record into an in-memory stored record."""
    tags = {}
    for ctx_val in cred.contexts:
        tags[f"ctxt:{ctx_val}"] = "1"
    for type_val in cred.expanded_types:
        tags[f"type:{type_val}"] = "1"
    for schema_val in cred.schema_ids:
        tags[f"schm:{schema_val}"] = "1"
    for subj_id in cred.subject_ids:
        tags[f"subj:{subj_id}"] = "1"
    for proof_type in cred.proof_types:
        tags[f"ptyp:{proof_type}"] = "1"
    if cred.issuer_id:
        tags["issuer_id"] = cred.issuer_id
    if cred.given_id:
        tags["given_id"] = cred.given_id
    if cred.cred_tags:
        tags.update(cred.cred_tags)

    return StorageRecord(
        VC_CRED_RECORD_TYPE,
        json.dumps(cred.cred_value),
        tags,
        cred.record_id,
    )
