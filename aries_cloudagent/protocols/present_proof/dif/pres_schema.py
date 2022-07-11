"""DIF Proof Schema."""
from marshmallow import fields

from ....messaging.models.openapi import OpenAPISchema
from ....messaging.valid import (
    StrOrDictField,
    UUIDFour,
)
from ....vc.vc_ld import LinkedDataProofSchema

from .pres_exch import PresentationSubmissionSchema


class DIFProofSchema(OpenAPISchema):
    """Schema for DIF Proof."""

    id = fields.Str(
        required=False,
        validate=UUIDFour(),
        metadata={"description": "ID", "example": UUIDFour.EXAMPLE},
    )
    contexts = fields.List(StrOrDictField(), data_key="@context", required=True)
    types = fields.List(
        fields.Str(metadata={"description": "Types"}), data_key="type", required=True
    )
    credentials = fields.List(
        fields.Dict(required=False, metadata={"description": "Credentials"}),
        data_key="verifiableCredential",
    )
    proof = fields.Nested(
        LinkedDataProofSchema(),
        required=False,
        metadata={"description": "The proof of the credential"},
    )
    presentation_submission = fields.Nested(PresentationSubmissionSchema())
