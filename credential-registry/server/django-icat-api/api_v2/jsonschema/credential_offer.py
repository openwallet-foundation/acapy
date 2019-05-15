CREDENTIAL_OFFER_JSON_SCHEMA = {
    # TODO: use newer draft of spec?
    "$schema": "http://json-schema.org/draft-04/schema",
    "type": "object",
    # TODO: Flesh out definitions further?
    "properties": {
        "credential_offer": {"type": "object"},
        "credential_definition_id": {"type": "string"},
    },
    "required": ["credential_offer", "credential_definition_id"],
}
