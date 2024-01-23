"""Verifiable Presentation model."""

from marshmallow import fields, Schema
from ...messaging.valid import (
    DIDKey,
    StrOrDictField,
    UriOrDictField,
    UUID4_EXAMPLE,
)
from ...vc.ld_proofs.constants import (
    CREDENTIALS_CONTEXT_V1_URL,
    VERIFIABLE_PRESENTATION_TYPE,
)
from .proofs import ProofSchema


class PresentationSchema(Schema):
    """Linked data presentation schema.

    Based on https://www.w3.org/TR/vc-data-model

    """

    context = fields.List(
        UriOrDictField(required=True),
        data_key="@context",
        required=True,
        metadata={
            "example": [CREDENTIALS_CONTEXT_V1_URL],
        },
    )
    id = fields.Str(
        data_key="id",
        required=False,
        metadata={
            "example": UUID4_EXAMPLE,
        },
    )
    type = fields.List(
        fields.Str(required=True),
        data_key="type",
        required=True,
        metadata={
            "example": [VERIFIABLE_PRESENTATION_TYPE],
        },
    )
    holder = StrOrDictField(
        data_key="holder",
        required=False,
        metadata={
            "example": DIDKey.EXAMPLE,
        },
    )
    verifiableCredential = fields.List(
        fields.Dict(required=True),
        data_key="verifiableCredential",
        required=False,
        metadata={
            "example": [{}],
        },
    )


class VerifiablePresentationSchema(PresentationSchema):
    """Single Verifiable Presentation Schema."""

    proof = fields.Nested(ProofSchema, data_key="proof", required=False)
