"""DIF Proof Schema."""
from marshmallow import fields

from ....messaging.models.openapi import OpenAPISchema
from ....messaging.valid import (
    UUID4,
    StrOrDictField,
)
from ....vc.vc_ld.models import LinkedDataProofSchema

from .pres_exch import PresentationSubmissionSchema


class DIFPresSpecSchema(OpenAPISchema):
    """Schema for DIF Proof."""

    id = fields.Str(
        description="ID",
        required=False,
        **UUID4,
        data_key="id",
    )
    contexts = fields.List(
        StrOrDictField(),
        data_key="@context",
        required=True,
    )
    types = fields.List(
        fields.Str(description="Types"),
        data_key="type",
        required=True,
    )
    credentials = fields.List(
        fields.Dict(description="Credentials", required=False),
        data_key="verifiableCredential",
    )
    proof = fields.Nested(
        LinkedDataProofSchema(),
        required=False,
        description="The proof of the credential",
        example={
            "type": "Ed25519Signature2018",
            "verificationMethod": (
                "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyG"
                "o38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
            ),
            "created": "2019-12-11T03:50:55",
            "proofPurpose": "assertionMethod",
            "jws": (
                "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0JiNjQiXX0..lKJU0Df"
                "_keblRKhZAS9Qq6zybm-HqUXNVZ8vgEPNTAjQKBhQDxvXNo7nvtUBb_Eq1Ch6YBKY5qBQ"
            ),
        },
        data_key="proof",
    )
    presentation_submission = fields.Nested(
        PresentationSubmissionSchema(), data_key="presentation_submission"
    )
