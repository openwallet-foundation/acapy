"""DIF Proof Request Schema."""
from marshmallow import fields, INCLUDE
from typing import Optional, Union

from ....messaging.models.base import BaseModel, BaseModelSchema
from ....messaging.models.openapi import OpenAPISchema

from .pres_exch import (
    PresentationDefinitionSchema,
    PresentationDefinition,
    DIFOptionsSchema,
    DIFOptions,
)


class DIFProofRequest(BaseModel):
    """DIF presentation request input detail."""

    class Meta:
        """DIFProofRequest metadata."""

        schema_class = "DIFProofRequestSchema"

    def __init__(
        self,
        presentation_definition: Optional[Union[dict, PresentationDefinition]],
        options: Optional[Union[dict, DIFOptions]] = None,
    ) -> None:
        """Initialize the DIFProofRequest instance."""
        self.presentation_definition = presentation_definition
        self.options = options


class DIFProofRequestSchema(BaseModelSchema):
    """Schema for DIF presentation request."""

    class Meta:
        """Accept parameter overload."""

        unknown = INCLUDE
        model_class = DIFProofRequest

    options = fields.Nested(
        DIFOptionsSchema(),
        required=False,
    )
    presentation_definition = fields.Nested(
        PresentationDefinitionSchema(),
        required=True,
    )


class DIFPresSpecSchema(OpenAPISchema):
    """Schema for DIF Presentation Spec schema."""

    issuer_id = fields.Str(
        description=(
            (
                "Issuer identifier to sign the presentation,"
                " if different from current public DID"
            )
        ),
        required=False,
    )
    record_ids = fields.Dict(
        description=(
            (
                "Mapping of input_descriptor id to list "
                "of stored W3C credential record_id"
            )
        ),
        example=(
            {
                "<input descriptor id_1>": ["<record id_1>", "<record id_2>"],
                "<input descriptor id_2>": ["<record id>"],
            }
        ),
        required=False,
    )
    presentation_definition = fields.Nested(
        PresentationDefinitionSchema(),
        required=False,
    )
    reveal_doc = fields.Dict(
        description=(
            "reveal doc [JSON-LD frame] dict used"
            " to derive the credential when selective"
            " disclosure is required"
        ),
        required=False,
        example={
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://w3id.org/security/bbs/v1",
            ],
            "type": ["VerifiableCredential", "LabReport"],
            "@explicit": True,
            "@requireAll": True,
            "issuanceDate": {},
            "issuer": {},
            "credentialSubject": {
                "Observation": [
                    {"effectiveDateTime": {}, "@explicit": True, "@requireAll": True}
                ],
                "@explicit": True,
                "@requireAll": True,
            },
        },
    )
