"""Presentation verification and validation result classes."""

from typing import List, Optional

from marshmallow import fields

from ...messaging.models.base import BaseModel, BaseModelSchema
from ...vc.ld_proofs.validation_result import DocumentVerificationResultSchema
from ..ld_proofs import DocumentVerificationResult


class PresentationVerificationResult(BaseModel):
    """Presentation verification result class."""

    class Meta:
        """PresentationVerificationResult metadata."""

        schema_class = "PresentationVerificationResultSchema"

    def __init__(
        self,
        *,
        verified: bool,
        presentation_result: Optional[DocumentVerificationResult] = None,
        credential_results: Optional[List[DocumentVerificationResult]] = None,
        errors: Optional[List[str]] = None,
    ) -> None:
        """Create new PresentationVerificationResult instance."""
        self.verified = verified
        self.presentation_result = presentation_result
        self.credential_results = credential_results
        self.errors = errors

    def __repr__(self) -> str:
        """Return a human readable representation of this class.

        Returns:
            A human readable string for this class

        """
        items = ("{}={}".format(k, repr(v)) for k, v in self.__dict__.items())
        return "<{}({})>".format(self.__class__.__name__, ", ".join(items))

    def __eq__(self, other: object) -> bool:
        """Comparison between presentation verification results."""
        if isinstance(other, PresentationVerificationResult):
            return (
                self.verified == other.verified
                and self.presentation_result == other.presentation_result
                # check credential results list
                and (
                    # both not present
                    (not self.credential_results and not other.credential_results)
                    # both list and matching
                    or (
                        isinstance(self.credential_results, list)
                        and isinstance(other.credential_results, list)
                        and all(
                            self_result == other_result
                            for (self_result, other_result) in zip(
                                self.credential_results, other.credential_results
                            )
                        )
                    )
                )
                # check error list
                and (
                    # both not present
                    (not self.errors and not other.errors)
                    # both list and matching
                    or (
                        isinstance(self.errors, list)
                        and isinstance(other.errors, list)
                        and all(
                            self_error == other_error
                            for (self_error, other_error) in zip(
                                self.errors, other.errors
                            )
                        )
                    )
                )
            )
        return False


class PresentationVerificationResultSchema(BaseModelSchema):
    """Presentation verification result schema."""

    class Meta:
        """PresentationVerificationResultSchema metadata."""

        model_class = PresentationVerificationResult

    verified = fields.Bool(required=True)
    presentation_result = fields.Nested(DocumentVerificationResultSchema)
    credential_results = fields.List(fields.Nested(DocumentVerificationResultSchema))
    errors = fields.List(fields.Str())
