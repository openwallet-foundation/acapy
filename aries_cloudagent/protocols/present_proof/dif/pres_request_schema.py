"""DIF Proof Request Schema."""
from typing import Optional, Union

from marshmallow import INCLUDE, fields

from ....messaging.models.base import BaseModel, BaseModelSchema
from ....messaging.models.openapi import OpenAPISchema
from .pres_exch import (
    DIFOptions,
    DIFOptionsSchema,
    PresentationDefinition,
    PresentationDefinitionSchema,
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

    options = fields.Nested(DIFOptionsSchema(), required=False)
    presentation_definition = fields.Nested(
        PresentationDefinitionSchema(), required=True
    )


class DIFPresSpecSchema(OpenAPISchema):
    """Schema for DIF Presentation Spec schema."""

    issuer_id = fields.Str(
        required=False,
        metadata={
            "description": (
                "Issuer identifier to sign the presentation, if different from current"
                " public DID"
            )
        },
    )
    record_ids = fields.Dict(
        required=False,
        metadata={
            "description": (
                "Mapping of input_descriptor id to list of stored W3C credential"
                " record_id"
            ),
            "example": {
                "<input descriptor id_1>": ["<record id_1>", "<record id_2>"],
                "<input descriptor id_2>": ["<record id>"],
            },
        },
    )
    presentation_definition = fields.Nested(
        PresentationDefinitionSchema(), required=False
    )
    reveal_doc = fields.Dict(
        required=False,
        metadata={
            "description": (
                "reveal doc [JSON-LD frame] dict used to derive the credential when"
                " selective disclosure is required"
            ),
            "example": {
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
                        {
                            "effectiveDateTime": {},
                            "@explicit": True,
                            "@requireAll": True,
                        }
                    ],
                    "@explicit": True,
                    "@requireAll": True,
                },
            },
        },
    )
