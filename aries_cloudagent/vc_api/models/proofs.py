"""LinkedDataProof."""

from marshmallow import fields, Schema

from ...messaging.valid import (
    RFC3339_DATETIME_EXAMPLE,
)


class ProofSchema(Schema):
    """Linked data proof schema.

    Based on https://w3c-ccg.github.io/ld-proofs

    """

    created = fields.Str(
        data_key="created",
        required=True,
        metadata={
            "example": RFC3339_DATETIME_EXAMPLE,
        },
    )
    type = fields.Str(
        data_key="type",
        required=True,
        metadata={
            "example": "Ed25519Signature2020",
        },
    )
    domain = fields.Str(
        data_key="domain",
        required=False,
        metadata={
            "example": "website.example",
        },
    )
    challenge = fields.Str(
        data_key="challenge",
        required=False,
        metadata={
            "example": "6e62f66e-67de-11eb-b490-ef3eeefa55f2",
        },
    )
    proofPurpose = fields.Str(
        data_key="proofPurpose",
        required=True,
        metadata={
            "example": "assertionMethod",
        },
    )
    verificationMethod = fields.Str(
        data_key="verificationMethod",
        required=True,
        metadata={
            "example": "did:example:123#key-01",
        },
    )
    jws = fields.Str(
        data_key="jws",
        required=False,
        metadata={
            "example": "eyJhbGciOiAiRWRE...BKY5qBQ",
        },
    )
    proofValue = fields.Str(
        data_key="proofValue",
        required=False,
        metadata={
            "example": "eyJhbGciOiAiRWRE...BKY5qBQ",
        },
    )
