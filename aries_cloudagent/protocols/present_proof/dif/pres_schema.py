"""DIF Proof Schema."""
from marshmallow import fields

from ....messaging.models.openapi import OpenAPISchema
from ....messaging.valid import (
    UUID4,
    StrOrDictField,
)
from ....vc.vc_ld import LinkedDataProofSchema

from .pres_exch import PresentationSubmissionSchema


class DIFProofSchema(OpenAPISchema):
    """Schema for DIF Proof."""

    id = fields.Str(
        description="ID",
        required=False,
        **UUID4,
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
    )
    presentation_submission = fields.Nested(PresentationSubmissionSchema())
