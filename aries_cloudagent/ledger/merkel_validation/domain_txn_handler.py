"""Utilities for Processing Replies to Domain Read Requests."""
import base58
import base64
import hashlib
import json

from binascii import hexlify
from copy import deepcopy

from .utils import audit_path_length
from .constants import (
    ACCUM_FROM,
    ACCUM_TO,
    ALL_ATR_KEYS,
    LAST_SEQ_NO,
    VAL,
    VALUE,
    HASH,
    LAST_UPDATE_TIME,
    MARKER_CLAIM_DEF,
    MARKER_SCHEMA,
    MARKER_ATTR,
    MARKER_REVOC_DEF,
    MARKER_REVOC_REG_ENTRY,
    MARKER_REVOC_REG_ENTRY_ACCUM,
    GET_NYM,
    GET_ATTR,
    GET_CLAIM_DEF,
    GET_REVOC_REG_DEF,
    GET_REVOC_REG_ENTRY,
    GET_REVOC_REG_DELTA,
    GET_SCHEMA,
    NYM,
    ATTRIB,
    SCHEMA,
    CLAIM_DEF,
    REVOC_REG_DEF,
    REVOC_REG_ENTRY,
    DEST,
    RESULT,
    DATA,
    SEQ_NO,
    TXN_METADATA,
    TXN_TIME,
    TXN,
    NAME,
    VERSION,
    ATTR_NAMES,
    FROM,
    METADATA,
    REF,
    CRED_DEF_ID,
    REVOC_DEF_TYPE,
    REVOC_DEF_TYPE_ID,
    AUDIT_PATH,
    ROOT_HASH,
    STATE_PROOF,
    STATE_PROOF_FROM,
    PROOF_NODES,
    TAG,
)


def _extract_attr_typed_value(txn_data):
    """Check for 'raw', 'enc', 'hash' in ATTR & GET_ATTR, return it's name and value."""
    existing_keys = [key for key in ALL_ATR_KEYS if key in txn_data]
    if len(existing_keys) == 0:
        raise ValueError(
            "ATTR should have one of the following fields: {}".format(ALL_ATR_KEYS)
        )
    if len(existing_keys) > 1:
        raise ValueError(
            "ATTR should have only one of the following fields: {}".format(ALL_ATR_KEYS)
        )
    existing_key = existing_keys[0]
    return existing_key, txn_data[existing_key]


def parse_attr_txn(txn_data):
    """Process txn_data and parse attr_txn based on attr_type."""
    attr_type, attr = _extract_attr_typed_value(txn_data)
    if attr_type == "raw":
        data = json.loads(attr)
        re_raw = json.dumps(data)
        key, _ = data.popitem()
        return attr_type, key, re_raw
    if attr_type == "enc":
        return attr_type, attr, attr
    if attr_type == "hash":
        return attr_type, attr, None


def encode_state_value(value, seqNo, txnTime):
    """Return encoded state value."""
    return json.dumps({LAST_SEQ_NO: seqNo, LAST_UPDATE_TIME: txnTime, VAL: value})


def decode_state_value(encoded_value):
    """Return val, lsn, lut from encoded state value."""
    decoded = json.loads(encoded_value)
    value = decoded.get(VAL)
    last_seq_no = decoded.get(LAST_SEQ_NO)
    last_update_time = decoded.get(LAST_UPDATE_TIME)
    return value, last_seq_no, last_update_time


def hash_of(text) -> str:
    """Return 256 bit hexadecimal digest of text."""
    if not isinstance(text, (str, bytes)):
        text = json.dumps(text)
    if not isinstance(text, bytes):
        text = text.encode()
    return hashlib.sha256(text).hexdigest()


def make_state_path_for_attr(did, attr_name, attr_is_hash=False) -> bytes:
    """Return state_path for ATTR."""
    nameHash = (
        hashlib.sha256(attr_name.encode()).hexdigest()
        if not attr_is_hash
        else attr_name
    )
    return "{DID}:{MARKER}:{ATTR_NAME}".format(
        DID=did, MARKER=MARKER_ATTR, ATTR_NAME=nameHash
    ).encode()


def prepare_get_attr_for_state(reply):
    """Return value for state from GET_ATTR."""
    attr_type, attr_key = _extract_attr_typed_value(reply)
    data = reply.get(DATA)
    value_bytes = None
    if data:
        result = reply.copy()
        data = result.pop(DATA)
        result[attr_type] = data
        attr_type, _, value = parse_attr_txn(result)
        hashed_value = hash_of(value) if value else ""
        seq_no = result.get(SEQ_NO)
        txn_time = result.get(TXN_TIME)
        value_bytes = encode_state_value(hashed_value, seq_no, txn_time)
    return value_bytes


def prepare_attr_for_state(txn, path_only=False):
    """Return key, value pair for state from ATTR."""
    txn_data = txn.get(TXN, {}).get(DATA)
    nym = txn_data.get(DEST)
    attr_type, attr_key, value = parse_attr_txn(txn_data)
    path = make_state_path_for_attr(nym, attr_key, attr_type == HASH)
    if path_only:
        return path
    hashed_value = hash_of(value) if value else ""
    seq_no = txn[TXN_METADATA].get(SEQ_NO)
    txn_time = txn[TXN_METADATA].get(TXN_TIME)
    value_bytes = encode_state_value(hashed_value, seq_no, txn_time)
    return path, value_bytes.encode()


def make_state_path_for_nym(did) -> bytes:
    """Return state_path for NYM."""
    return hashlib.sha256(did.encode()).digest()


def prepare_nym_for_state(txn):
    """Return encoded state path from NYM."""
    txn_data = txn.get(TXN, {}).get(DATA)
    nym = txn_data.get(DEST)
    path = make_state_path_for_nym(nym)
    return hexlify(path).decode()


def prepare_get_nym_for_state(reply):
    """Return value for state from GET_NYM."""
    data = reply.get(DATA)
    value = None
    if data is not None:
        if isinstance(data, str):
            data = json.loads(data)
        data.pop(DEST, None)
        value = json.dumps(data)
    return value


def prepare_get_schema_for_state(reply):
    """Return value for state from GET_SCHEMA."""
    value_bytes = None
    attr_names = reply[DATA].get(ATTR_NAMES)
    if attr_names:
        data = {ATTR_NAMES: attr_names}
        seq_no = reply.get(SEQ_NO)
        txn_time = reply.get(TXN_TIME)
        value_bytes = encode_state_value(data, seq_no, txn_time)
    return value_bytes


def make_state_path_for_schema(authors_did, schema_name, schema_version) -> bytes:
    """Return state_path for SCHEMA."""
    return "{DID}:{MARKER}:{SCHEMA_NAME}:{SCHEMA_VERSION}".format(
        DID=authors_did,
        MARKER=MARKER_SCHEMA,
        SCHEMA_NAME=schema_name,
        SCHEMA_VERSION=schema_version,
    ).encode()


def prepare_schema_for_state(txn, path_only=False):
    """Return key-value pair for state from SCHEMA."""
    origin = txn[TXN].get(METADATA, {}).get(FROM)
    schema_name = txn[TXN][DATA][DATA].get(NAME)
    schema_version = txn[TXN][DATA][DATA].get(VERSION)
    value = {ATTR_NAMES: txn[TXN][DATA][DATA].get(ATTR_NAMES)}
    path = make_state_path_for_schema(origin, schema_name, schema_version)
    if path_only:
        return path
    seq_no = txn[TXN_METADATA].get(SEQ_NO)
    txn_time = txn[TXN_METADATA].get(TXN_TIME)
    value_bytes = encode_state_value(value, seq_no, txn_time)
    return path, value_bytes.encode()


def prepare_get_claim_def_for_state(reply):
    """Return value for state from GET_CLAIM_DEF."""
    schema_seq_no = reply.get(REF)
    if schema_seq_no is None:
        raise ValueError("ref field is absent, but it must contain schema seq no")
    value_bytes = None
    data = reply.get(DATA)
    if data is not None:
        seq_no = reply.get(SEQ_NO)
        txn_time = reply.get(TXN_TIME)
        value_bytes = encode_state_value(data, seq_no, txn_time)
    return value_bytes


def make_state_path_for_claim_def(authors_did, schema_seq_no, signature_type, tag):
    """Return state_path for CLAIM DEF."""
    return "{DID}:{MARKER}:{SIGNATURE_TYPE}:{SCHEMA_SEQ_NO}:{TAG}".format(
        DID=authors_did,
        MARKER=MARKER_CLAIM_DEF,
        SIGNATURE_TYPE=signature_type,
        SCHEMA_SEQ_NO=schema_seq_no,
        TAG=tag,
    ).encode()


def prepare_claim_def_for_state(txn, path_only=False):
    """Return key-value pair for state from CLAIM_DEF."""
    origin = txn[TXN].get(METADATA, {}).get(FROM)
    schema_seq_no = txn[TXN][DATA].get(REF)
    if schema_seq_no is None:
        raise ValueError("ref field is absent, but it must contain schema seq no")
    data = txn[TXN][DATA].get(DATA)
    if data is None:
        raise ValueError("data field is absent, but it must contain components of keys")
    signature_type = txn[TXN][DATA].get("signature_type", "CL")
    tag = txn[TXN][DATA].get(TAG, "tag")
    path = make_state_path_for_claim_def(origin, schema_seq_no, signature_type, tag)
    if path_only:
        return path
    seq_no = txn[TXN_METADATA].get(SEQ_NO)
    txn_time = txn[TXN_METADATA].get(TXN_TIME)
    value_bytes = encode_state_value(data, seq_no, txn_time)
    return path, value_bytes.encode()


def prepare_get_revoc_def_for_state(reply):
    """Return value for state from GET_REVOC_DEF."""
    seq_no = reply.get(SEQ_NO)
    txn_time = reply.get(TXN_TIME)
    value_bytes = encode_state_value(reply.get(DATA), seq_no, txn_time)
    return value_bytes


def make_state_path_for_revoc_def(
    authors_did, cred_def_id, revoc_def_type, revoc_def_tag
) -> bytes:
    """Return state_path for REVOC_DEF."""
    return "{DID}:{MARKER}:{CRED_DEF_ID}:{REVOC_DEF_TYPE}:{REVOC_DEF_TAG}".format(
        DID=authors_did,
        MARKER=MARKER_REVOC_DEF,
        CRED_DEF_ID=cred_def_id,
        REVOC_DEF_TYPE=revoc_def_type,
        REVOC_DEF_TAG=revoc_def_tag,
    ).encode()


def prepare_revoc_def_for_state(txn, path_only=False):
    """Return key-value pair for state from REVOC_DEF."""
    author_did = txn[TXN].get(METADATA, {}).get(FROM, None)
    txn_data = txn[TXN].get(DATA)
    cred_def_id = txn_data.get(CRED_DEF_ID)
    revoc_def_type = txn_data.get(REVOC_DEF_TYPE)
    revoc_def_tag = txn_data.get(TAG)
    path = make_state_path_for_revoc_def(
        author_did, cred_def_id, revoc_def_type, revoc_def_tag
    )
    if path_only:
        return path
    seq_no = txn[TXN_METADATA].get(SEQ_NO)
    txn_time = txn[TXN_METADATA].get(TXN_TIME)
    value_bytes = encode_state_value(txn_data, seq_no, txn_time)
    return path, value_bytes.encode()


def prepare_get_revoc_reg_entry_for_state(reply):
    """Return value for state from GET_REVOC_REG_ENTRY."""
    if RESULT in reply.keys():
        result = reply.get(RESULT)
    else:
        result = reply
    seq_no = result.get(SEQ_NO)
    txn_time = result.get(TXN_TIME)
    value_bytes = encode_state_value(result.get(DATA), seq_no, txn_time)
    return value_bytes


def make_state_path_for_revoc_reg_entry(revoc_reg_def_id) -> bytes:
    """Return state_path for REVOC_REG_ENTRY."""
    return "{MARKER}:{REVOC_REG_DEF_ID}".format(
        MARKER=MARKER_REVOC_REG_ENTRY, REVOC_REG_DEF_ID=revoc_reg_def_id
    ).encode()


def prepare_get_revoc_reg_delta_for_state(reply):
    """Return value for state from GET_REVOC_REG_DELTA."""
    if STATE_PROOF_FROM in reply[DATA]:
        accum_to_seq_no = reply[DATA][VALUE].get(ACCUM_TO, {}).get(SEQ_NO)
        accum_to_txn_time = reply[DATA][VALUE].get(ACCUM_TO, {}).get(TXN_TIME)
        accum_from_seq_no = reply[DATA][VALUE].get(ACCUM_FROM, {}).get(SEQ_NO)
        accum_from_txn_time = reply[DATA][VALUE].get(ACCUM_FROM, {}).get(TXN_TIME)
        return (
            encode_state_value(
                reply[DATA][VALUE].get(ACCUM_TO),
                accum_to_seq_no,
                accum_to_txn_time,
            ),
            encode_state_value(
                reply[DATA][VALUE].get(ACCUM_FROM),
                accum_from_seq_no,
                accum_from_txn_time,
            ),
        )
    else:
        seq_no = reply.get(SEQ_NO)
        txn_time = reply.get(TXN_TIME)
        return encode_state_value(reply[DATA][VALUE].get(ACCUM_TO), seq_no, txn_time)


def prepare_revoc_reg_entry_for_state(txn, path_only=False):
    """Return key-value pair for state from REVOC_REG_ENTRY."""
    txn_data = txn[TXN].get(DATA)
    revoc_reg_def_id = txn_data.get(REVOC_DEF_TYPE_ID)
    path = make_state_path_for_revoc_reg_entry(revoc_reg_def_id=revoc_reg_def_id)
    if path_only:
        return path
    seq_no = txn[TXN_METADATA].get(SEQ_NO)
    txn_time = txn[TXN_METADATA].get(TXN_TIME)
    txn_data = deepcopy(txn_data)
    txn_data[SEQ_NO] = seq_no
    txn_data[TXN_TIME] = txn_time
    value_bytes = encode_state_value(txn_data, seq_no, txn_time)
    return path, value_bytes.encode()


def prepare_get_revoc_reg_entry_accum_for_state(reply):
    """Return value for state from GET_REVOC_REG_ENTRY_ACCUM."""
    seq_no = reply.get(SEQ_NO)
    txn_time = reply.get(TXN_TIME)
    value_bytes = encode_state_value(reply.get(DATA), seq_no, txn_time)
    return value_bytes


def make_state_path_for_revoc_reg_entry_accum(revoc_reg_def_id) -> bytes:
    """Return state_path for REVOC_REG_ENTRY_ACCUM."""
    return "{MARKER}:{REVOC_REG_DEF_ID}".format(
        MARKER=MARKER_REVOC_REG_ENTRY_ACCUM, REVOC_REG_DEF_ID=revoc_reg_def_id
    ).encode()


def prepare_revoc_reg_entry_accum_for_state(txn):
    """Return key-value pair for state from REVOC_REG_ENTRY_ACCUM."""
    if RESULT in txn.keys():
        result = txn.get(RESULT)
    else:
        result = txn
    txn_data = result[TXN].get(DATA)
    revoc_reg_def_id = txn_data.get(REVOC_DEF_TYPE_ID)
    seq_no = result[TXN_METADATA].get(SEQ_NO)
    txn_time = result[TXN_METADATA].get(TXN_TIME)
    path = make_state_path_for_revoc_reg_entry_accum(revoc_reg_def_id=revoc_reg_def_id)
    txn_data = deepcopy(txn_data)
    txn_data[SEQ_NO] = seq_no
    txn_data[TXN_TIME] = txn_time
    value_bytes = encode_state_value(txn_data, seq_no, txn_time)
    return path, value_bytes.encode()


def extract_params_write_request(data):
    """Return tree_size, leaf_index, audit_path, expected_root_hash from reply."""
    if RESULT in data.keys():
        data = data.get(RESULT)
    tree_size = data[TXN_METADATA].get(SEQ_NO)
    leaf_index = tree_size - 1
    audit_path = data.get(AUDIT_PATH)
    audit_path = audit_path[:]
    decoded_audit_path = [
        base58.b58decode(hash_str.encode("utf-8")) for hash_str in audit_path
    ]
    expected_root_hash = base58.b58decode(data.get(ROOT_HASH).encode("utf-8"))
    if len(decoded_audit_path) != audit_path_length(leaf_index, tree_size):
        raise Exception("auditPath length does not match with given seqNo")
    return tree_size, leaf_index, decoded_audit_path, expected_root_hash


def get_proof_nodes(reply):
    """Return proof_nodes from reply."""
    if RESULT in reply.keys():
        reply = reply.get(RESULT)
    if reply.get("type") == GET_REVOC_REG_DELTA and STATE_PROOF_FROM in reply.get(DATA):
        proof_nodes_accum_to = reply[STATE_PROOF].get(PROOF_NODES)
        proof_nodes_accum_from = reply[DATA].get(STATE_PROOF_FROM, {}).get(PROOF_NODES)
        return base64.b64decode(proof_nodes_accum_to), base64.b64decode(
            proof_nodes_accum_from
        )
    else:
        b64_encoded_nodes = reply[STATE_PROOF].get(PROOF_NODES)
        return base64.b64decode(b64_encoded_nodes)


def prepare_for_state_read(reply):
    """Return state value from read requests reply."""
    if RESULT in reply.keys():
        reply = reply.get(RESULT)
    request_type = reply.get("type")
    if request_type == GET_ATTR:
        return prepare_get_attr_for_state(reply=reply)
    if request_type == GET_NYM:
        return prepare_get_nym_for_state(reply=reply)
    if request_type == GET_SCHEMA:
        return prepare_get_schema_for_state(reply=reply)
    if request_type == GET_CLAIM_DEF:
        return prepare_get_claim_def_for_state(reply=reply)
    if request_type == GET_REVOC_REG_DEF:
        return prepare_get_revoc_def_for_state(reply=reply)
    if request_type == GET_REVOC_REG_ENTRY:
        return prepare_get_revoc_reg_entry_accum_for_state(reply=reply)
    if request_type == GET_REVOC_REG_DELTA:
        if "issued" in reply[DATA].get("value"):
            return prepare_get_revoc_reg_delta_for_state(reply=reply)
        else:
            return prepare_get_revoc_reg_entry_accum_for_state(reply=reply)
    raise ValueError(
        "Cannot make state value for request of type {}".format(request_type)
    )


def prepare_for_state_write(reply):
    """Return state key, value pair from write requests reply."""
    if RESULT in reply.keys():
        reply = reply.get(RESULT)
    request_type = reply[TXN].get("type")
    if request_type == NYM:
        return prepare_nym_for_state(txn=reply)
    if request_type == ATTRIB:
        return prepare_attr_for_state(txn=reply)
    if request_type == SCHEMA:
        return prepare_schema_for_state(txn=reply)
    if request_type == CLAIM_DEF:
        return prepare_claim_def_for_state(txn=reply)
    if request_type == REVOC_REG_DEF:
        return prepare_revoc_def_for_state(txn=reply)
    if request_type == REVOC_REG_ENTRY:
        return prepare_revoc_reg_entry_for_state(txn=reply)
    raise ValueError(
        "Cannot make state key-value pair for request of type {}".format(request_type)
    )
