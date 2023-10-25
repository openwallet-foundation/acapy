"""Verifiable Presentation model."""

from typing import Optional, Sequence, Union

from marshmallow import INCLUDE, fields
from ....messaging.models.base import BaseModel, BaseModelSchema
from ....messaging.valid import UUID4_EXAMPLE, UUID4_VALIDATE, StrOrDictField
from .linked_data_proof import LinkedDataProofSchema


class VerifiablePresentation(BaseModel):
    """Single VerifiablePresentation object."""

    class Meta:
        """VerifiablePresentation metadata."""

        schema_class = "VerifiablePresentationSchema"
        unknown = INCLUDE

    def __init__(
        self,
        *,
        id: Optional[str] = None,
        contexts: Optional[Sequence[Union[str, dict]]] = None,
        types: Optional[Sequence[str]] = None,
        credentials: Optional[Sequence[dict]] = None,
        proof: Optional[Sequence[dict]] = None,
        **kwargs,
    ):
        """Initialize VerifiablePresentation."""
        super().__init__()
        self.id = id
        self.contexts = contexts
        self.types = types
        self.credentials = credentials
        self.proof = proof


class VerifiablePresentationSchema(BaseModelSchema):
    """Single Verifiable Presentation Schema."""

    class Meta:
        """VerifiablePresentationSchema metadata."""

        model_class = VerifiablePresentation
        unknown = INCLUDE

    id = fields.Str(
        required=False,
        validate=UUID4_VALIDATE,
        metadata={"description": "ID", "example": UUID4_EXAMPLE},
    )
    contexts = fields.List(StrOrDictField(), data_key="@context")
    types = fields.List(
        fields.Str(required=False, metadata={"description": "Types"}), data_key="type"
    )
    credentials = fields.List(
        fields.Dict(required=False, metadata={"description": "Credentials"}),
        data_key="verifiableCredential",
    )
    proof = fields.Nested(
        LinkedDataProofSchema(),
        required=True,
        metadata={"description": "The proof of the credential"},
    )
