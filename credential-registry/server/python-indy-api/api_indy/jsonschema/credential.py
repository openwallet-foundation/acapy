CREDENTIAL_JSON_SCHEMA = {
    # TODO: use newer draft of spec?
    "$schema": "http://json-schema.org/draft-04/schema",
    "type": "object",
    # TODO: Flesh out definitions further?
    "properties": {
        "credential_data": {"type": "object"},
        "credential_request_metadata": {"type": "object"},
    },
    "required": ["credential_data", "credential_request_metadata"],
}
