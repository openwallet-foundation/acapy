CONSTRUCT_PROOF_JSON_SCHEMA = {
    # TODO: use newer draft of spec?
    "$schema": "http://json-schema.org/draft-04/schema",
    "type": "object",
    # TODO: Flesh out definitions further?
    "properties": {"proof_request": {"type": "object"}},
    "required": ["proof_request"],
}
