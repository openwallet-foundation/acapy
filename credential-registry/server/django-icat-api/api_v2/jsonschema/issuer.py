ISSUER_JSON_SCHEMA = {
    "$schema": "http://json-schema.org/draft-04/schema",
    "type": "object",
    "properties": {
        "issuer": {
            "type": "object",
            "properties": {
                # check length + valid characters?
                "did": {"type": "string", "minLength": 1},
                "name": {"type": "string", "minLength": 1},
                "abbreviation": {"type": "string"},
                "email": {"type": "string", "minLength": 1},
                "url": {"type": "string"},
                "endpoint": {"type": "string"},
            },
            "required": ["did", "name"],
        },
        "credential_types": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "schema": {"type": "string", "minLength": 1},
                    "version": {"type": "string", "minLength": 1},
                    "description": {"type": "string", "minLength": 1},
                    "endpoint": {"type": "string"},
                    # TODO: validate name OR type/srcid
                    "topic": {
                        "oneOf": [{"type": "object"}, {"type": "array"}]
                    },
                    "credential": {"type": "object"},
                    "mapping": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "model": {"type": "string", "minLength": 1},
                                "cardinality_fields": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                # TODO: validate field structure?
                                "fields": {"type": "object"},
                            },
                        },
                    },
                },
                "required": ["name", "schema", "version", "topic"],
            },
        },
    },
    "required": ["issuer"],
}
