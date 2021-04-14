"""Linked data proof verifiable options detail artifacts to attach to RFC 453 messages."""


from typing import Optional, Union
from marshmallow import fields, INCLUDE


from .......vc.vc_ld import CredentialSchema
from .......messaging.models.base import BaseModel, BaseModelSchema
from .......vc.vc_ld.models.credential import (
    VerifiableCredential,
)
from .cred_detail_options import LDProofVCDetailOptionsSchema, LDProofVCDetailOptions


class LDProofVCDetail(BaseModel):
    """Linked data proof verifiable credential detail."""

    class Meta:
        """LDProofVCDetail metadata."""

        schema_class = "LDProofVCDetailSchema"

    def __init__(
        self,
        credential: Optional[Union[dict, VerifiableCredential]],
        options: Optional[Union[dict, LDProofVCDetailOptions]],
    ) -> None:
        """Initialize the LDProofVCDetail instance."""
        if isinstance(credential, dict):
            credential = VerifiableCredential.deserialize(credential)
        self.credential = credential

        if isinstance(options, dict):
            options = LDProofVCDetailOptions.deserialize(options)
        self.options = options

    def __eq__(self, other: object) -> bool:
        """Comparison between linked data vc details."""
        if isinstance(other, LDProofVCDetail):
            return self.credential == other.credential and self.options == other.options
        return False


class LDProofVCDetailSchema(BaseModelSchema):
    """Linked data proof verifiable credential detail schema."""

    class Meta:
        """Accept parameter overload."""

        unknown = INCLUDE
        model_class = LDProofVCDetail

    credential = fields.Nested(
        CredentialSchema(),
        required=True,
        description="Detail of the JSON-LD Credential to be issued",
    )

    options = fields.Nested(
        LDProofVCDetailOptionsSchema(),
        required=True,
        description="Options for specifying how the linked data proof is created.",
    )
