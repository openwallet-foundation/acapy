"""DID routes web requests schemas."""

from marshmallow import fields, Schema


class DIDKeyRegistrationRequest(Schema):
    """Request schema for creating a dids."""

    type = fields.Str(
        default="ed25519",
        required=False,
        metadata={
            "description": "Key Type",
            "example": "ed25519",
        },
    )

    seed = fields.Str(
        default=None,
        required=False,
        metadata={
            "description": "Seed",
            "example": "00000000000000000000000000000000",
        },
    )

    kid = fields.Str(
        default=None,
        required=False,
        metadata={
            "description": "Verification Method",
            "example": "did:web:example.com#key-01",
        },
    )


class DIDKeyRegistrationResponse(Schema):
    """Response schema for creating a did."""

    did = fields.Str()
    multikey = fields.Str()
    verificationMethod = fields.Str()


class DIDKeyBindingRequest(Schema):
    """Request schema for binding a kid to a did."""

    did = fields.Str(
        default=None,
        required=True,
        metadata={
            "description": "DID",
            "example": "did:key:z6MkgKA7yrw5kYSiDuQFcye4bMaJpcfHFry3Bx45pdWh3s8i",
        },
    )

    kid = fields.Str(
        default=None,
        required=True,
        metadata={
            "description": "Verification Method",
            "example": "did:web:example.com#key-02",
        },
    )


class DIDKeyBindingResponse(Schema):
    """Response schema for binding a kid to a did."""

    did = fields.Str()
    multikey = fields.Str()
    verificationMethod = fields.Str()
