"""DataIntegrityProof."""

from typing import List, Optional

from marshmallow import INCLUDE, fields

from ....messaging.models.base import BaseModel, BaseModelSchema
from .proof import DataIntegrityProof, DataIntegrityProofSchema


class ProblemDetails(BaseModel):
    """ProblemDetails model."""

    class Meta:
        """ProblemDetails metadata."""

        schema_class = "ProblemDetailsSchema"

    def __init__(
        self,
        type: Optional[str] = None,
        title: Optional[str] = None,
        detail: Optional[str] = None,
    ) -> None:
        """Initialize the ProblemDetails instance."""

        self.type = type
        self.title = title
        self.detail = detail


class ProblemDetailsSchema(BaseModelSchema):
    """ProblemDetails schema.

    Based on https://www.w3.org/TR/vc-data-model-2.0/#problem-details.

    """

    class Meta:
        """Accept parameter overload."""

        unknown = INCLUDE
        model_class = ProblemDetails

    type = fields.Str(
        required=True,
        metadata={
            "example": "https://w3id.org/security#PROOF_VERIFICATION_ERROR",
        },
    )

    title = fields.Str(
        required=False,
        metadata={},
    )

    detail = fields.Str(
        required=False,
        metadata={},
    )


class DataIntegrityVerificationResult(BaseModel):
    """Data Integrity Verification Result model."""

    class Meta:
        """DataIntegrityVerificationResult metadata."""

        schema_class = "DataIntegrityVerificationResultSchema"

    def __init__(
        self,
        verified: Optional[bool] = None,
        proof: Optional[DataIntegrityProof] = None,
        problem_details: Optional[List[ProblemDetails]] = None,
    ) -> None:
        """Initialize the DataIntegrityVerificationResult instance."""

        self.verified = verified
        self.proof = proof
        self.problem_details = problem_details


class DataIntegrityVerificationResultSchema(BaseModelSchema):
    """DataIntegrityVerificationResult schema."""

    class Meta:
        """Accept parameter overload."""

        unknown = INCLUDE
        model_class = DataIntegrityVerificationResult

    verified = fields.Bool(
        required=True,
        metadata={
            "example": False,
        },
    )

    proof = fields.Nested(
        DataIntegrityProofSchema(),
        required=True,
        metadata={},
    )

    problem_details = fields.List(
        fields.Nested(ProblemDetailsSchema()),
        data_key="problemDetails",
        required=True,
        metadata={},
    )


class DataIntegrityVerificationResponse(BaseModel):
    """Data Integrity Verification Response model."""

    class Meta:
        """DataIntegrityVerificationResponse metadata."""

        schema_class = "DataIntegrityVerificationResponseSchema"

    def __init__(
        self,
        verified: Optional[bool] = None,
        verified_document: Optional[dict] = None,
        results: Optional[List[DataIntegrityVerificationResult]] = None,
    ) -> None:
        """Initialize the DataIntegrityVerificationResponse instance."""

        self.verified = verified
        self.verified_document = verified_document
        self.results = results


class DataIntegrityVerificationResponseSchema(BaseModelSchema):
    """DataIntegrityVerificationResponse schema."""

    class Meta:
        """Accept parameter overload."""

        unknown = INCLUDE
        model_class = DataIntegrityVerificationResponse

    verified = fields.Bool(
        required=True,
        metadata={
            "example": False,
        },
    )

    verified_document = fields.Dict(
        data_key="verifiedDocument",
        required=False,
        metadata={},
    )

    results = fields.List(
        fields.Nested(DataIntegrityVerificationResultSchema()),
        required=False,
        metadata={},
    )
