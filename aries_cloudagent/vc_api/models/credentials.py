"""Verifiable Credential marshmallow schema classes."""

from marshmallow import fields, Schema

from ...messaging.valid import (
    CREDENTIAL_SUBJECT_EXAMPLE,
    CREDENTIAL_STATUS_EXAMPLE,
    RFC3339_DATETIME_EXAMPLE,
    UUID4_EXAMPLE,
    DictOrDictListField,
    DIDKey,
    StrOrDictField,
    UriOrDictField,
)
from ...vc.ld_proofs.constants import (
    CREDENTIALS_CONTEXT_V1_URL,
    VERIFIABLE_CREDENTIAL_TYPE,
)
from .proofs import ProofSchema


class CredentialSchema(Schema):
    """Linked data credential schema.

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
            "example": [VERIFIABLE_CREDENTIAL_TYPE],
        },
    )
    issuer = StrOrDictField(
        data_key="issuer",
        required=True,
        metadata={
            "example": DIDKey.EXAMPLE,
        },
    )
    issuanceDate = fields.Str(
        data_key="issuanceDate",
        required=True,
        metadata={
            "example": RFC3339_DATETIME_EXAMPLE,
        },
    )
    expirationDate = fields.Str(
        data_key="expirationDate",
        required=False,
        metadata={
            "example": RFC3339_DATETIME_EXAMPLE,
        },
    )
    credentialSubject = DictOrDictListField(
        data_key="credentialSubject",
        required=True,
        metadata={
            "example": CREDENTIAL_SUBJECT_EXAMPLE,
        },
    )
    credentialStatus = DictOrDictListField(
        data_key="credentialStatus",
        required=False,
        metadata={
            "example": CREDENTIAL_STATUS_EXAMPLE,
        },
    )


class VerifiableCredentialSchema(CredentialSchema):
    """Linked data verifiable credential schema.

    Based on https://www.w3.org/TR/vc-data-model

    """

    proof = fields.Nested(ProofSchema)
