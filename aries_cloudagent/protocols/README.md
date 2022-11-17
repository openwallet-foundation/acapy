# Creating Protocols

Protocols that are added to this directory will be loaded automatically on startup. It is also possible load external protocol implementations. For example, [this protocol](https://github.com/bcgov/aries-vcr/tree/master/server/message_families/issuer_registration) implementation is built as a separate python package and explicitly loaded at startup with the `--plugin indy_catalyst_issuer_registration` parameter.

## Directory Structure

```
├── __init__.py
├── definition.py
└── v1_0
    ├── __init__.py
    ├── handlers
    │   ├── __init__.py
    │   ├── credential_ack_handler.py
    │   ├── credential_issue_handler.py
    │   ├── credential_offer_handler.py
    │   ├── credential_proposal_handler.py
    │   ├── credential_request_handler.py
    │   └── tests
    │       ├── __init__.py
    │       ├── test_credential_ack_handler.py
    │       ├── test_credential_issue_handler.py
    │       ├── test_credential_offer_handler.py
    │       ├── test_credential_proposal_handler.py
    │       └── test_credential_request_handler.py
    ├── manager.py
    ├── message_types.py
    ├── messages
    │   ├── __init__.py
    │   ├── credential_ack.py
    │   ├── credential_issue.py
    │   ├── credential_offer.py
    │   ├── credential_proposal.py
    │   ├── credential_request.py
    │   ├── inner
    │   │   ├── __init__.py
    │   │   ├── credential_preview.py
    │   │   └── tests
    │   │       ├── __init__.py
    │   │       └── test_credential_preview.py
    │   └── tests
    │       ├── __init__.py
    │       ├── test_credential_ack.py
    │       ├── test_credential_issue.py
    │       ├── test_credential_offer.py
    │       ├── test_credential_proposal.py
    │       └── test_credential_request.py
    ├── models
    │   ├── __init__.py
    │   └── credential_exchange.py
    ├── routes.py
    └── tests
        ├── __init__.py
        ├── test_manager.py
        └── test_routes.py
```

### `definition.py`

The top level directory should contain a `definition.py` module with information about the protocol implementation.

The contents of the file should be as follows:

```
versions = [
    {
        "major_version": 1,
        "minimum_minor_version": 0,
        "current_minor_version": 0,
        "path": "v1_0",
    }
]
```

Each implementation can have any number of major versions each with a different module path. Each major version is effectively a separate protocol except in name. Each major version must have exactly 1 minor version. The definition also specifies a minimum minor version that your implementation supports.

### protocol package

Protocols must specify a `message_types.py` module as well as any number of messages and handlers for handling agent messages. The package can also optionally specify a `routes.py` module which can be used to add admin API endpoints alongside your protocol implementation.

Use the protocols implemented in this directory as a guide.